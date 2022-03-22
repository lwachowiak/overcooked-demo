import numpy as np
import csv, sys, getopt
from matplotlib import pyplot as plt
import pandas as pd
from pathlib import Path
import os

#  parameters are the CSV files that contain the gaze position and agent positions acquired from the world frame,
def match_gaze_to_agents(input_agents, input_gaze, start_frame, end_frame):
    ###################### CHANGE HERE ################################
    thresh = 40
    out_filepath = Path('gaze_agent_merged/' + input_agents[28:-11] + "merged.csv")
    video_res = [1280, 720]
    ###################################################################
    # Helper function to get the Euclidean distance
    def Euclidean_Dist(df1, df2, cols, cols2):
        return np.linalg.norm(df1[cols].values - df2[cols2].values,
                       axis=1)

    # flip to the top-left coordinate frame to align openCV and Pupil Labs data, convert normalised to absolute

    gaze = pd.read_csv(input_gaze, engine="python")
    agents = pd.read_csv(input_agents, engine="python")

    gaze_median = gaze.groupby("world_index").median()[['norm_pos_x', 'norm_pos_y']]
    gaze_median['norm_pos_y'] = 1 - gaze_median["norm_pos_y"]
    gaze_median['norm_pos_x'] = gaze_median['norm_pos_x']*video_res[0]
    gaze_median['norm_pos_y'] = gaze_median['norm_pos_y']*video_res[1]
    human_agent = agents[["Human x", "Human y"]]
    ai_agent = agents[["Agent x", "Agent y"]]

    # Calculate distances between objects of interest (gaze pos - human player and gaze pos - AI player)
    distances = pd.concat([gaze_median, agents], axis=1)
    distances["gaze_to_human"] = Euclidean_Dist(gaze_median, human_agent, ['norm_pos_x', 'norm_pos_y'], ["Human x", "Human y"])
    distances["gaze_to_ai"] = Euclidean_Dist(gaze_median, ai_agent, ['norm_pos_x', 'norm_pos_y'], ["Agent x", "Agent y"])
    distances["Gaze_focus"] = 0
    distances.loc[(distances["gaze_to_human"] > thresh) & (distances["gaze_to_ai"] > thresh),"Gaze_focus"] = "Env"
    distances.loc[(distances["gaze_to_human"] < thresh) & (distances["gaze_to_ai"] > thresh),"Gaze_focus"] = "Human"
    distances.loc[(distances["gaze_to_human"] > thresh) & (distances["gaze_to_ai"] < thresh),"Gaze_focus"] = "AI"
    distances.loc[(distances["gaze_to_human"] < thresh) & (distances["gaze_to_ai"] < thresh) & (distances["gaze_to_human"] < distances["gaze_to_ai"]),"Gaze_focus"] = "Human"
    distances.loc[(distances["gaze_to_human"] < thresh) & (distances["gaze_to_ai"] < thresh) & (distances["gaze_to_human"] > distances["gaze_to_ai"]),"Gaze_focus"] = "AI"
    distances["Condition"] = "TODO"

    distances=distances.iloc[start_frame:end_frame]

    distances.to_csv(out_filepath)


# list of start and end frames
lvl1_start=[39,  7,   24,  37,  49,  90,  18,  39,  15,   30,  0, 41,  25,16,36,41,18,20,  329, 36,  124, 22,  36, 0, 56, 0, 30, 47, 38, 63, 61, 0, 33, 0, 29]
lvl2_start=[17, 26, 18 , 34,  0 ,  59,  25 , 13 , 5 , 17, 0, 11, 24, 20, 11,  13, 21 , 23,  97 , 33 , 29 , 20 , 37, 0, 46, 0, 20, 66 , 39 , 50,  59, 0,27, 0, 32]   
lvl1_end=[1070, 1017, 1032,    1057,    1015,    1131,    1093,    1100,    1002,    1049, 0, 1075,  996, 1137  ,  1188 ,   1083 ,   1103  ,  1143  ,  1446 ,   1117  ,  1179  ,  986, 1056, 0, 1068, 0, 1098, 1065, 1055,  1164, 1099, 0, 1010, 0, 1090]
lvl2_end=[1025,  983, 841, 1088 ,   968, 1065  ,  1067,    1049,    1072   , 988, 0, 1049,    997, 1125 ,   1090 ,   1008 ,   1081 ,   1121 ,   1196 ,   1097  ,  1077 ,   982, 1021, 0, 1045, 0,   1061 ,   1084 ,   1056  ,  1111,    1145, 0, 998, 0, 1078]  

# annotate all csvs in folder position_monitor_annotation
path = "position_monitor_annotation"
directories = sorted(os.listdir( path ))

participant_counter=-1 
for ag_file in directories:
    if ag_file[-3:]=="csv":
        participant=ag_file[0:3]
        lvl=ag_file[4:7]
        if lvl=="000": 
            participant_counter+=1
            start_frame = lvl1_start[participant_counter]
            end_frame = lvl1_end[participant_counter]
        else:
            start_frame = lvl2_start[participant_counter]
            end_frame = lvl2_end[participant_counter]

        input_gaze = "HRI-Experiment-1-Data/"+participant+"/"+lvl+"/exports/000/gaze_positions.csv"

        print("merging "+ag_file+" and "+input_gaze, "from", start_frame, "to", end_frame)
        try: 
            match_gaze_to_agents(input_agents="position_monitor_annotation/"+ag_file, input_gaze=input_gaze, start_frame=start_frame, end_frame=end_frame)
        except Exception as err: 
            print("merginging failed "+ag_file+" and "+input_gaze)
            print(err)
