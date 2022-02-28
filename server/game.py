from abc import ABC, abstractmethod
from threading import Lock, Thread
from queue import Queue, LifoQueue, Empty, Full
from time import time
from overcooked_ai_py.mdp.overcooked_mdp import OvercookedGridworld
from overcooked_ai_py.mdp.overcooked_env import OvercookedEnv
from overcooked_ai_py.mdp.actions import Action, Direction
from overcooked_ai_py.planning.planners import MotionPlanner, NO_COUNTERS_PARAMS
#from human_aware_rl.rllib.rllib import load_agent
import random, os, pickle, json
#import ray

# Relative path to where all static pre-trained agents are stored on server
AGENT_DIR = None

# Maximum allowable game time (in seconds)
MAX_GAME_TIME = 90

GAME_ROUND = 0

def _configure(max_game_time, agent_dir):
    global AGENT_DIR, MAX_GAME_TIME
    MAX_GAME_TIME = max_game_time
    AGENT_DIR = agent_dir

class Game(ABC):

    """
    Class representing a game object. Coordinates the simultaneous actions of arbitrary
    number of players. Override this base class in order to use. 

    Players can post actions to a `pending_actions` queue, and driver code can call `tick` to apply these actions.


    It should be noted that most operations in this class are not on their own thread safe. Thus, client code should
    acquire `self.lock` before making any modifications to the instance. 

    One important exception to the above rule is `enqueue_actions` which is thread safe out of the box
    """

    # Possible TODO: create a static list of IDs used by the class so far to verify id uniqueness
    # This would need to be serialized, however, which might cause too great a performance hit to 
    # be worth it

    EMPTY = 'EMPTY'
    
    class Status:
        DONE = 'done'
        ACTIVE = 'active'
        RESET = 'reset'
        INACTIVE = 'inactive'
        ERROR = 'error'



    def __init__(self, *args, **kwargs):
        """
        players (list): List of IDs of players currently in the game
        spectators (set): Collection of IDs of players that are not allowed to enqueue actions but are currently watching the game
        id (int):   Unique identifier for this game
        pending_actions List[(Queue)]: Buffer of (player_id, action) pairs have submitted that haven't been commited yet
        lock (Lock):    Used to serialize updates to the game state
        is_active(bool): Whether the game is currently being played or not
        """
        self.players = []
        self.spectators = set()
        self.pending_actions = []
        self.id = kwargs.get('id', id(self))
        self.lock = Lock()
        self._is_active = False

    @abstractmethod
    def is_full(self):
        """
        Returns whether there is room for additional players to join or not
        """
        pass

    @abstractmethod
    def apply_action(self, player_idx, action):
        """
        Updates the game state by applying a single (player_idx, action) tuple. Subclasses should try to override this method
        if possible
        """
        pass


    @abstractmethod
    def is_finished(self):
        """
        Returns whether the game has concluded or not
        """
        pass

    def is_ready(self):
        """
        Returns whether the game can be started. Defaults to having enough players
        """
        return self.is_full()

    @property
    def is_active(self):
        """
        Whether the game is currently being played
        """
        return self._is_active

    @property
    def reset_timeout(self):
        """
        Number of milliseconds to pause game on reset
        """
        return 3000

    def apply_actions(self):
        """
        Updates the game state by applying each of the pending actions in the buffer. Is called by the tick method. Subclasses
        should override this method if joint actions are necessary. If actions can be serialized, overriding `apply_action` is 
        preferred
        """
        for i in range(len(self.players)):
            try:
                while True:
                    action = self.pending_actions[i].get(block=False)
                    self.apply_action(i, action)
            except Empty:
                pass

    def activate(self):
        """
        Activates the game to let server know real-time updates should start. Provides little functionality but useful as
        a check for debugging
        """
        self._is_active = True

    def deactivate(self):
        """
        Deactives the game such that subsequent calls to `tick` will be no-ops. Used to handle case where game ends but 
        there is still a buffer of client pings to handle
        """
        self._is_active = False

    def reset(self):
        """
        Restarts the game while keeping all active players by resetting game stats and temporarily disabling `tick`
        """
        if not self.is_active:
            raise ValueError("Inactive Games cannot be reset")
        if self.is_finished():
            return self.Status.DONE
        self.deactivate()
        self.activate()
        return self.Status.RESET

    def needs_reset(self):
        """
        Returns whether the game should be reset on the next call to `tick`
        """
        return False


    def tick(self):
        """
        Updates the game state by applying each of the pending actions. This is done so that players cannot directly modify
        the game state, offering an additional level of safety and thread security. 

        One can think of "enqueue_action" like calling "git add" and "tick" like calling "git commit"

        Subclasses should try to override `apply_actions` if possible. Only override this method if necessary
        """ 
        if not self.is_active:
            return self.Status.INACTIVE
        if self.needs_reset():
            self.reset()
            return self.Status.RESET

        self.apply_actions()
        return self.Status.DONE if self.is_finished() else self.Status.ACTIVE
    
    def enqueue_action(self, player_id, action):
        """
        Add (player_id, action) pair to the pending action queue, without modifying underlying game state

        Note: This function IS thread safe
        """
        if not self.is_active:
            # Could run into issues with is_active not being thread safe
            return
        if player_id not in self.players:
            # Only players actively in game are allowed to enqueue actions
            return
        try:
            player_idx = self.players.index(player_id)
            self.pending_actions[player_idx].put(action)
        except Full:
            pass

    def get_state(self):
        """
        Return a JSON compatible serialized state of the game. Note that this should be as minimalistic as possible
        as the size of the game state will be the most important factor in game performance. This is sent to the client
        every frame update.
        """
        return { "players" : self.players }

    def to_json(self):
        """
        Return a JSON compatible serialized state of the game. Contains all information about the game, does not need to
        be minimalistic. This is sent to the client only once, upon game creation
        """
        return self.get_state()

    def is_empty(self):
        """
        Return whether it is safe to garbage collect this game instance
        """
        return not self.num_players

    def add_player(self, player_id, idx=None, buff_size=-1):
        """
        Add player_id to the game
        """
        if self.is_full():
            raise ValueError("Cannot add players to full game")
        if self.is_active:
            raise ValueError("Cannot add players to active games")
        if not idx and self.EMPTY in self.players:
            idx = self.players.index(self.EMPTY)
        elif not idx:
            idx = len(self.players)
        
        padding = max(0, idx - len(self.players) + 1)
        for _ in range(padding):
            self.players.append(self.EMPTY)
            self.pending_actions.append(self.EMPTY)
        
        self.players[idx] = player_id
        self.pending_actions[idx] = Queue(maxsize=buff_size)

    def add_spectator(self, spectator_id):
        """
        Add spectator_id to list of spectators for this game
        """
        if spectator_id in self.players:
            raise ValueError("Cannot spectate and play at same time")
        self.spectators.add(spectator_id)

    def remove_player(self, player_id):
        """
        Remove player_id from the game
        """
        try:
            idx = self.players.index(player_id)
            self.players[idx] = self.EMPTY
            self.pending_actions[idx] = self.EMPTY
        except ValueError:
            return False
        else:
            return True

    def remove_spectator(self, spectator_id):
        """
        Removes spectator_id if they are in list of spectators. Returns True if spectator successfully removed, False otherwise
        """
        try:
            self.spectators.remove(spectator_id)
        except ValueError:
            return False
        else:
            return True


    def clear_pending_actions(self):
        """
        Remove all queued actions for all players
        """
        for i, player in enumerate(self.players):
            if player != self.EMPTY:
                queue = self.pending_actions[i]
                queue.queue.clear()

    @property
    def num_players(self):
        return len([player for player in self.players if player != self.EMPTY])

    def get_data(self):
        """
        Return any game metadata to server driver. Really only relevant for Psiturk code
        """
        return {}

class OvercookedGame(Game):
    """
    Class for bridging the gap between Overcooked_Env and the Game interface

    Instance variable:
        - max_players (int): Maximum number of players that can be in the game at once
        - mdp (OvercookedGridworld): Controls the underlying Overcooked game logic
        - score (int): Current reward acheived by all players
        - max_time (int): Number of seconds the game should last
        - npc_policies (dict): Maps user_id to policy (Agent) for each AI player
        - npc_state_queues (dict): Mapping of NPC user_ids to LIFO queues for the policy to process
        - curr_tick (int): How many times the game server has called this instance's `tick` method
        - ticker_per_ai_action (int): How many frames should pass in between NPC policy forward passes. 
            Note that this is a lower bound; if the policy is computationally expensive the actual frames
            per forward pass can be higher
        - action_to_overcooked_action (dict): Maps action names returned by client to action names used by OvercookedGridworld
            Note that this is an instance variable and not a static variable for efficiency reasons
        - human_players (set(str)): Collection of all player IDs that correspond to humans
        - npc_players (set(str)): Collection of all player IDs that correspond to AI
        - randomized (boolean): Whether the order of the layouts should be randomized
    
    Methods:
        - npc_policy_consumer: Background process that asynchronously computes NPC policy forward passes. One thread
            spawned for each NPC
        - _curr_game_over: Determines whether the game on the current mdp has ended
    """

    def __init__(self, layouts=["forced_coordination_KCL"], mdp_params={}, num_players=2, gameTime=90, playerZero='human', playerOne='human', showPotential=False, randomized=False, **kwargs):
        super(OvercookedGame, self).__init__(**kwargs)

        global GAME_ROUND
        GAME_ROUND+=1
        if GAME_ROUND==1:
            #layouts=["tutorial_1"]
            layouts=["forced_coordination_KCL"]
        else:
            layouts=["counter_circuit_KCL"]

        playerZero="human"
        playerOne="notHuman"

        self.show_potential = showPotential
        self.mdp_params = mdp_params
        self.layouts = layouts
        self.max_players = int(num_players)
        self.mdp = None
        self.mp = None
        self.score = 0
        self.phi = 0
        self.max_time = min(int(gameTime), MAX_GAME_TIME)
        self.npc_policies = {}
        self.npc_state_queues = {}
        self.action_to_overcooked_action = {
            "STAY" : Action.STAY,
            "UP" : Direction.NORTH,
            "DOWN" : Direction.SOUTH,
            "LEFT" : Direction.WEST,
            "RIGHT" : Direction.EAST,
            "SPACE" : Action.INTERACT
        }
        self.ticks_per_ai_action = 4
        self.curr_tick = 0
        self.human_players = set()
        self.npc_players = set()
        self.hint = ""

        if randomized:
            random.shuffle(self.layouts)

        if playerZero != 'human':
            player_zero_id = playerZero + '_0'
            self.add_player(player_zero_id, idx=0, buff_size=1, is_human=False)
            self.npc_policies[player_zero_id] = self.get_policy(playerZero, idx=0)
            self.npc_state_queues[player_zero_id] = LifoQueue()

        if playerOne != 'human':
            player_one_id = playerOne + '_1'
            self.add_player(player_one_id, idx=1, buff_size=1, is_human=False)
            self.npc_policies[player_one_id] = self.get_policy(playerOne, idx=1)
            self.npc_state_queues[player_one_id] = LifoQueue()
        

    def _curr_game_over(self):
        return time() - self.start_time >= self.max_time


    def needs_reset(self):
        return self._curr_game_over() and not self.is_finished()

    def add_player(self, player_id, idx=None, buff_size=-1, is_human=True):
        super(OvercookedGame, self).add_player(player_id, idx=idx, buff_size=buff_size)
        if is_human:
            self.human_players.add(player_id)
        else:
            self.npc_players.add(player_id)

    def remove_player(self, player_id):
        removed = super(OvercookedGame, self).remove_player(player_id)
        if removed:
            if player_id in self.human_players:
                self.human_players.remove(player_id)
            elif player_id in self.npc_players:
                self.npc_players.remove(player_id)
            else:
                raise ValueError("Inconsistent state")


    def npc_policy_consumer(self, policy_id):
        queue = self.npc_state_queues[policy_id]
        policy = self.npc_policies[policy_id]
        while self._is_active:
            state = queue.get()
            npc_action, _ = policy.action(state)
            super(OvercookedGame, self).enqueue_action(policy_id, npc_action)


    def is_full(self):
        return self.num_players >= self.max_players

    def is_finished(self):
        val = not self.layouts and self._curr_game_over()
        return val

    def is_empty(self):
        """
        Game is considered safe to scrap if there are no active players or if there are no humans (spectating or playing)
        """
        return super(OvercookedGame, self).is_empty() or not self.spectators and not self.human_players

    def is_ready(self):
        """
        Game is ready to be activated if there are a sufficient number of players and at least one human (spectator or player)
        """
        return super(OvercookedGame, self).is_ready() and not self.is_empty()

    def apply_action(self, player_id, action):
        pass

    def apply_actions(self):
        # Default joint action, as NPC policies and clients probably don't enqueue actions fast 
        # enough to produce one at every tick
        joint_action = [Action.STAY] * len(self.players)

        # Synchronize individual player actions into a joint-action as required by overcooked logic
        for i in range(len(self.players)):
            try:
                joint_action[i] = self.pending_actions[i].get(block=False)
            except Empty:
                pass
        
        # Apply overcooked game logic to get state transition
        prev_state = self.state
        self.state, info = self.mdp.get_state_transition(prev_state, joint_action)
        if self.show_potential:
            self.phi = self.mdp.potential_function(prev_state, self.mp, gamma=0.99)

        # Send next state to all background consumers if needed
        if self.curr_tick % self.ticks_per_ai_action == 0:
            for npc_id in self.npc_policies:
                self.npc_state_queues[npc_id].put(self.state, block=False)

        # Update score based on soup deliveries that might have occured
        curr_reward = sum(info['sparse_reward_by_agent'])
        self.score += curr_reward

        # update hint
        #if self.layouts[0]=="forced_coordination_KCL" and self.score == 0 and max(self.max_time - (time() - self.start_time), 0)<75:
        if self.score == 0 and max(self.max_time - (time() - self.start_time), 0)<75 and self.curr_layout=="forced_coordination_KCL":
            self.hint="The tomatoes are in the cupboard on the bottom right"
        else:
            self.hint=""
        print("LAYOUT")
        print(self.curr_layout, flush=True)

        # Return about the current transition
        return prev_state, joint_action, info
        

    def enqueue_action(self, player_id, action):
        overcooked_action = self.action_to_overcooked_action[action]
        super(OvercookedGame, self).enqueue_action(player_id, overcooked_action)

    def reset(self):
        status = super(OvercookedGame, self).reset()
        if status == self.Status.RESET:
            # Hacky way of making sure game timer doesn't "start" until after reset timeout has passed
            self.start_time += self.reset_timeout / 1000


    def tick(self):
        self.curr_tick += 1
        return super(OvercookedGame, self).tick()

    def activate(self):
        super(OvercookedGame, self).activate()

        # Sanity check at start of each game
        if not self.npc_players.union(self.human_players) == set(self.players):
            raise ValueError("Inconsistent State")

        self.curr_layout = self.layouts.pop()
        self.mdp = OvercookedGridworld.from_layout_name(self.curr_layout, **self.mdp_params)
        if self.show_potential:
            self.mp = MotionPlanner.from_pickle_or_compute(self.mdp, counter_goals=NO_COUNTERS_PARAMS)
        self.state = self.mdp.get_standard_start_state()
        if self.show_potential:
            self.phi = self.mdp.potential_function(self.state, self.mp, gamma=0.99)
        self.start_time = time()
        self.curr_tick = 0
        self.score = 0
        self.threads = []
        for npc_policy in self.npc_policies:
            self.npc_policies[npc_policy].reset()
            self.npc_state_queues[npc_policy].put(self.state)
            t = Thread(target=self.npc_policy_consumer, args=(npc_policy,))
            self.threads.append(t)
            t.start()

    def deactivate(self):
        super(OvercookedGame, self).deactivate()
        # Ensure the background consumers do not hang
        for npc_policy in self.npc_policies:
            self.npc_state_queues[npc_policy].put(self.state)

        # Wait for all background threads to exit
        for t in self.threads:
            t.join()

        # Clear all action queues
        self.clear_pending_actions()


    def get_state(self):
        state_dict = {}
        state_dict['potential'] = self.phi if self.show_potential else None
        state_dict['state'] = self.state.to_dict()
        state_dict['score'] = self.score
        state_dict['time_left'] = max(self.max_time - (time() - self.start_time), 0)
        state_dict['hint'] = self.hint
        return state_dict

    def to_json(self):
        obj_dict = {}
        obj_dict['terrain'] = self.mdp.terrain_mtx if self._is_active else None
        obj_dict['state'] = self.get_state() if self._is_active else None
        return obj_dict

    def get_policy(self, npc_id, idx=0):
        global GAME_ROUND
        if GAME_ROUND==1:
            return Level1_AI(self)
            # return StayAI()
        else:
            return Level2_AI(self)

class OvercookedTutorial(OvercookedGame):

    """
    Wrapper on OvercookedGame that includes additional data for tutorial mechanics, most notably the introduction of tutorial "phases"

    Instance Variables:
        - curr_phase (int): Indicates what tutorial phase we are currently on
        - phase_two_score (float): The exact sparse reward the user must obtain to advance past phase 2
    """
    

    def __init__(self, layouts=["tutorial_0"], mdp_params={}, playerZero='human', playerOne='AI', phaseTwoScore=15, **kwargs):
        super(OvercookedTutorial, self).__init__(layouts=layouts, mdp_params=mdp_params, playerZero=playerZero, playerOne=playerOne, showPotential=False, **kwargs)
        self.phase_two_score = phaseTwoScore
        self.phase_two_finished = False
        self.max_time = 0
        self.max_players = 2
        self.ticks_per_ai_action = 8
        self.curr_phase = 0

    @property
    def reset_timeout(self):
        return 1

    def needs_reset(self):
        if self.curr_phase == 0:
            return self.score > 0
        elif self.curr_phase == 1:
            return self.score > 0
        elif self.curr_phase == 2:
            return self.phase_two_finished
        return False 

    def is_finished(self):
        return not self.layouts and self.score >= float('inf')

    def reset(self):
        super(OvercookedTutorial, self).reset()
        self.curr_phase += 1

    def get_policy(self, *args, **kwargs):
        return TutorialAI()

    def apply_actions(self):
        """
        Apply regular MDP logic with retroactive score adjustment tutorial purposes
        """
        _, _, info = super(OvercookedTutorial, self).apply_actions()

        human_reward, ai_reward = info['sparse_reward_by_agent']

        # We only want to keep track of the human's score in the tutorial
        self.score -= ai_reward

        # Phase two requires a specific reward to complete
        if self.curr_phase == 2:
            self.score = 0
            if human_reward == self.phase_two_score:
                self.phase_two_finished = True
  
class StayAI():
    """
    Always returns "stay" action. Used for debugging
    """
    def action(self, state):
        return Action.STAY, None

    def reset(self):
        pass

class Level1_AI():
    """
    Hard-coded AI for forced-coordination level
    """

    CORRECT_LOOP = [
        # Grab first onion
        Direction.WEST,
        Action.INTERACT,
        Direction.NORTH,
        Direction.EAST,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.INTERACT,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,

        # Grab second onion
        Direction.WEST,
        Action.INTERACT,
        Direction.NORTH,
        Direction.EAST,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.INTERACT,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,

        # Grab a plate
        Direction.SOUTH,
        Direction.SOUTH,
        Direction.WEST,
        Action.INTERACT,
        Direction.NORTH,
        Direction.NORTH,
        Direction.EAST,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.INTERACT,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Direction.NORTH
    ]

    ERROR_LOOP_1 = [
    # Grab 3 onions instead of 2

        # Grab first onion
        Direction.WEST,
        Action.INTERACT,
        Direction.NORTH,
        Direction.EAST,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.INTERACT,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,

        # Grab second onion
        Direction.WEST,
        Action.INTERACT,
        Direction.NORTH,
        Direction.EAST,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.INTERACT,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,

        # Grab third onion
        Direction.WEST,
        Action.INTERACT,
        Direction.NORTH,
        Direction.EAST,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.INTERACT,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,

        # Grab a plate
        Direction.SOUTH,
        Direction.SOUTH,
        Direction.WEST,
        Action.INTERACT,
        Direction.NORTH,
        Direction.NORTH,
        Direction.EAST,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.INTERACT,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Direction.NORTH
    ]

    ERROR_LOOP_2 = [
    # Give plate too early

        # Grab first onion
        Direction.WEST,
        Action.INTERACT,
        Direction.NORTH,
        Direction.EAST,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.INTERACT,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,

        # Grab a plate
        Direction.SOUTH,
        Direction.SOUTH,
        Direction.WEST,
        Action.INTERACT,
        Direction.NORTH,
        Direction.NORTH,
        Direction.EAST,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.INTERACT,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Direction.NORTH,

        # Grab second onion
        Direction.WEST,
        Action.INTERACT,
        Direction.NORTH,
        Direction.EAST,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.INTERACT,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
    ]

    def __init__(self, overcookedgame):
        self.curr_tick = -1
        self.error_tick = -1
        self.loops_before_error=2
        self.error_state=0
        self.overcookedgame=overcookedgame

    def action(self, state):
        #check if sth is on the counter
        game_state = self.overcookedgame.get_state() if self.overcookedgame._is_active else None
        st_objects = game_state["state"]["objects"] 
        object_on_counter = False
        for obj in st_objects:
            if obj["position"]==(2,1):
                object_on_counter = True
        #execute actions based on whether there is sth on the counter or not        
        if object_on_counter:
            # wait when sth is still on the counter
            return Action.STAY, None    
        else:                           
            # execute correct loop x times
            if self.curr_tick<self.loops_before_error*(len(self.CORRECT_LOOP)-1):      
                self.curr_tick += 1
                return self.CORRECT_LOOP[self.curr_tick % len(self.CORRECT_LOOP)], None
            # execute error 1
            elif self.error_state==0:
                self.error_tick += 1                    
                act = self.ERROR_LOOP_1[self.error_tick % len(self.ERROR_LOOP_1)], None 
                if self.error_tick==len(self.ERROR_LOOP_1)-1:
                    self.reset()
                    self.error_state=1
                return act
            # execute error 2
            else:
                self.error_tick += 1                    
                act = self.ERROR_LOOP_2[self.error_tick % len(self.ERROR_LOOP_2)], None 
                if self.error_tick==len(self.ERROR_LOOP_2)-1:
                    self.reset()
                    self.error_state=0
                return act
    
    
    def reset(self):
        self.curr_tick = -1
        self.error_tick = -1 
    

class Level2_AI():
    """
    Hard-coded AI for circuit-counter level
    """

    CORRECT_LOOP = [
        # Place first tomato
        Direction.EAST,
        Direction.SOUTH,
        Action.INTERACT,
        Direction.NORTH,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.INTERACT,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,

        # Place first onion
        Direction.WEST,
        Direction.WEST,
        Direction.SOUTH,
        Action.INTERACT,
        Direction.NORTH,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.INTERACT,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,

        # Place second onion
        Direction.SOUTH,
        Action.INTERACT,
        Direction.NORTH,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.INTERACT,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,    
    ]

    SERVE_DISH_LOOP = [
        # Pick dish and serve
        Direction.EAST,
        Direction.NORTH,
        Action.INTERACT,
        Direction.SOUTH,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.INTERACT,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
    ]

    ERROR_LOOP = [
        # move up and place an ingredient in the pot
        
        # get onion
        Direction.WEST,
        Direction.SOUTH,
        Action.INTERACT,

        # move to pot and place onion 
        Direction.WEST,
        Direction.WEST,
        Direction.NORTH,
        Direction.NORTH,
        Direction.EAST,
        Direction.EAST,
        Direction.NORTH,
        Action.INTERACT,

        # move back
        Direction.WEST,
        Direction.WEST,
        Direction.SOUTH,
        Direction.SOUTH,
        Direction.EAST,
        Direction.EAST,
        Direction.EAST,

        # place tomato and second onion 
        Direction.EAST,
        Direction.SOUTH,
        Action.INTERACT,
        Direction.NORTH,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.INTERACT,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,

        Direction.WEST,
        Direction.WEST,
        Direction.SOUTH,
        Action.INTERACT,
        Direction.NORTH,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.INTERACT,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY
    ]

    def __init__(self, overcookedgame):
        self.curr_tick = 0
        self.error_tick = 0
        self.dish_loop_tick = 0
        self.successful_loops=0
        self.overcookedgame=overcookedgame
        self.soup_ready = False
        self.serve_is_done = False

    def action(self, state):

        #check if sth is on the counter
        game_state = self.overcookedgame.get_state() if self.overcookedgame._is_active else None
        st_objects = game_state["state"]["objects"] 
        object_on_counter = False
        dish_on_counter = False
        for obj in st_objects:
            if obj["position"]==(3,2):
                object_on_counter = True
        for obj in st_objects:
            if obj["position"]==(4,2) and obj["name"]=='soup':
                self.soup_ready = True

        # if there is no rdy soup to deliver        
        if not self.soup_ready:
            # if the error should be played
            if self.successful_loops==2:
                act = self.ERROR_LOOP[self.error_tick], None
                if self.path_blocked(act):
                    return Action.STAY, None
                else:
                    self.error_tick+=1
                    if self.error_tick == len(self.ERROR_LOOP):
                        self.error_tick = 0
                        self.successful_loops = -1
                        self.soup_ready = False
                        self.serve_is_done = True
                        self.dish_loop_tick = 0
                        self.curr_tick = 0 
                    return act 
            # wait while ingredients are on counter
            elif object_on_counter or self.serve_is_done:
                return Action.STAY, None
            # provide ingredients
            elif self.curr_tick % 35 != 0 or self.curr_tick == 0:
                act = self.CORRECT_LOOP[self.curr_tick % len(self.CORRECT_LOOP)], None
                if self.path_blocked(act):
                    return Action.STAY, None 
                else:
                    self.curr_tick += 1
                    return act
            # wait for soup to be returned
            else:
                self.serve_is_done = True
                return Action.STAY, None
        # if soup is on the counter then bring it to the delivery station       
        elif self.soup_ready:
            if self.dish_loop_tick < len(self.SERVE_DISH_LOOP):
                act = self.SERVE_DISH_LOOP[self.dish_loop_tick % len(self.SERVE_DISH_LOOP)], None
                if self.path_blocked(act):
                    return Action.STAY, None
                else:
                    self.dish_loop_tick+=1
                    return act
            # soup delivered
            else:
                self.successful_loops += 1
                self.curr_tick = 0
                self.dish_loop_tick = 0
                self.soup_ready = False
                self.serve_is_done = False
                return Action.STAY, None


    # returns true if the next action "would" would lead to a collision with the human               
    def path_blocked(self, act):
        if str(act[0])=="interact":
            return False
        else:
            # player 0 is human, 1 is agent
            human_pos = self.overcookedgame.get_state()["state"]["players"][0]["position"]
            agent_pos = self.overcookedgame.get_state()["state"]["players"][1]["position"]

            if agent_pos[0]+act[0][0]==human_pos[0] and agent_pos[1]+act[0][1]==human_pos[1]:
                print("BLOCKED", flush=True)
                return True 
            else:
                return False

    def reset(self):
        self.curr_tick = -1
        self.dish_loop_tick = -1
        self.error_tick = 0
        return self

    def tuple_add(self,x,y):
     z = []
     for i in range(len(x)):
         z.append(x[i]+y[i])
     return tuple(z)



class TutorialAI():

    COOK_SOUP_LOOP = [
        # Grab first onion
        Direction.WEST,
        Direction.WEST,
        Direction.WEST,
        Action.INTERACT,

        # Place onion in pot
        Direction.EAST,
        Direction.NORTH,
        Action.INTERACT,

        # Grab second onion
        Direction.WEST,
        Action.INTERACT,

        # Place onion in pot
        Direction.EAST,
        Direction.NORTH,
        Action.INTERACT,

        # Grab third onion
        Direction.WEST,
        Action.INTERACT,

        # Place onion in pot
        Direction.EAST,
        Direction.NORTH,
        Action.INTERACT,

        # Cook soup
        Action.INTERACT,
        
        # Grab plate
        Direction.EAST,
        Direction.SOUTH,
        Action.INTERACT,
        Direction.WEST,
        Direction.NORTH,

        # Deliver soup
        Action.INTERACT,
        Direction.EAST,
        Direction.EAST,
        Direction.EAST,
        Action.INTERACT,
        Direction.WEST
    ]

    COOK_SOUP_COOP_LOOP = [
        # Grab first onion
        Direction.WEST,
        Direction.WEST,
        Direction.WEST,
        Action.INTERACT,

        # Place onion in pot
        Direction.EAST,
        Direction.SOUTH,
        Action.INTERACT,

        # Move to start so this loops
        Direction.EAST,
        Direction.EAST,

        # Pause to make cooperation more real time
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY,
        Action.STAY
    ]

    def __init__(self):
        self.curr_phase = -1
        self.curr_tick = -1

    def action(self, state):
        self.curr_tick += 1
        if self.curr_phase == 0:
            return self.COOK_SOUP_LOOP[self.curr_tick % len(self.COOK_SOUP_LOOP)], None
        elif self.curr_phase == 2:
            return self.COOK_SOUP_COOP_LOOP[self.curr_tick % len(self.COOK_SOUP_COOP_LOOP)], None
        return Action.STAY, None

    def reset(self):
        self.curr_tick = -1
        self.curr_phase += 1
