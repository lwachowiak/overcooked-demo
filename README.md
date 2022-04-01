# Overcooked Demo
<p align="center">
<img src="./server/static/images/browser_view.png" >
</p>

This fork of Human-compatible AI's Overcooked Demo has been modified for use in experiments on importance of eye gaze in human-AI collaboration, carried out at King's College London in 2022 by P. Tisnikar and L. Wachowiak. The custom environment contains 2 levels, forced_coordination and counter_circuit, with modified graphics to hide tomatos in a cupboard in order to confuse the players. Added functionality includes integration with eye-tracking software.

The server uses a custom branch of the original overcooked-ai game environment that can be found [here](https://github.com/Ptisni/overcooked_ai). This environment contains the modified layouts, player starting positions, and recipes used in the experiments, along with suspension of cooking unless all 3 ingredients are present in the pot.

It is recommended that any new adaptation of these environments originates from the source repositories which can be found below:
[Overcooked Demo](https://github.com/HumanCompatibleAI/overcooked-demo)
[Overcooked game logic](https://github.com/HumanCompatibleAI/overcooked_ai)
[Human-aware RL](https://github.com/HumanCompatibleAI/human_aware_rl)

## Installation (From HCAI)

Building the server image requires [Docker](https://docs.docker.com/get-docker/)

## Usage

The server can be deployed locally using the driver script included in the repo. To run the production server, use the command
```bash
./up.sh production
```
In order to build and run the development server, which includes helpful debugging logs, run
```bash
./up.sh
```

After running one of the above commands, navigate to http://localhost

In order to kill the production server, run
```bash
./down.sh
```
## Making changes
If you want to make any changes to the environment start looking at these files:
* For Agent Policies: `game.py`
* For Page Layout: `index.html` and `overcooked_graphics_v2.2.js`
* For Game Graphics: `Terrain.png`and `Chefs.png`
* Server Communication: `app.py`
* Game Logic: look into https://github.com/Ptisni/overcooked_ai


