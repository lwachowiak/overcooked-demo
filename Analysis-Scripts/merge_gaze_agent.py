import numpy as np
import csv, sys, getopt
from matplotlib import pyplot as plt
import pandas as pd
from pathlib import Path
import os

#  parameters are the CSV files that contain the gaze position and agent positions acquired from the world frame,
def match_gaze_to_agents(input_agents, input_gaze):
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

    distances.to_csv(out_filepath)

# annotate all csvs in folder position_monitor_annotation
path = "position_monitor_annotation"
directories = sorted(os.listdir( path ))
 
for ag_file in directories:
    if ag_file[-3:]=="csv":
        participant=ag_file[0:3]
        lvl=ag_file[4:7]
        input_gaze="HRI-Experiment-1-Data/"+participant+"/"+lvl+"/exports/000/gaze_positions.csv"
        #print("merging "+ag_file+" and "+input_gaze)
        try: 
            match_gaze_to_agents(input_agents="position_monitor_annotation/"+ag_file, input_gaze=input_gaze)
        except Exception as err: 
            print("merginging failed "+ag_file+" and "+input_gaze)
            print(err)
