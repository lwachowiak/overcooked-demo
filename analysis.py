import numpy as np
import csv, sys, getopt
from matplotlib import pyplot as plt
import pandas as pd
from pathlib import Path
from datetime import datetime
###################### CHANGE HERE ################################
thresh = 40
filepath = Path('/home/peter/recordings/analysis_' + str(datetime.now()) + ".csv")
video_res = [1280, 720]
###################################################################
# Helper function to get the Euclidean distance
def Euclidean_Dist(df1, df2, cols, cols2):
    return np.linalg.norm(df1[cols].values - df2[cols2].values,
                   axis=1)

#  Load the CSV files that contain the gaze position and agent positions acquired from the world frame,
# flip to the top-left coordinate frame to align openCV and Pupil Labs data, convert normalised to absolute

input_gaze = input("Please input full path to gaze CSV file \n")
input_agents = input("Please input full path to agents CSV file \n")

gaze = pd.read_csv(input_gaze)
agents = pd.read_csv(input_agents)

gaze_median = gaze.groupby("world_index").median()[['norm_pos_x', 'norm_pos_y']]
gaze_median['norm_pos_y'] = 1 - gaze_median["norm_pos_y"]
gaze_median['norm_pos_x'] = gaze_median['norm_pos_x']*video_res[0]
gaze_median['norm_pos_y'] = gaze_median['norm_pos_y']*video_res[1]
human_agent = agents[["Human X", "Human y"]]
ai_agent = agents[["Agent x", "Agent y"]]

# Calculate distances between objects of interest (gaze pos - human player and gaze pos - AI player)
distances = pd.concat([gaze_median, agents], axis=1)
distances["gaze_to_human"] = Euclidean_Dist(gaze_median, human_agent, ['norm_pos_x', 'norm_pos_y'], ["Human X", "Human y"])
distances["gaze_to_ai"] = Euclidean_Dist(gaze_median, ai_agent, ['norm_pos_x', 'norm_pos_y'], ["Agent x", "Agent y"])
distances["Gaze_focus"] = 0
distances.loc[(distances["gaze_to_human"] > thresh) & (distances["gaze_to_ai"] > thresh),"Gaze_focus"] = "Env"
distances.loc[(distances["gaze_to_human"] < thresh) & (distances["gaze_to_ai"] > thresh),"Gaze_focus"] = "Human"
distances.loc[(distances["gaze_to_human"] > thresh) & (distances["gaze_to_ai"] < thresh),"Gaze_focus"] = "AI"
distances.loc[(distances["gaze_to_human"] < thresh) & (distances["gaze_to_ai"] < thresh) & (distances["gaze_to_human"] < distances["gaze_to_ai"]),"Gaze_focus"] = "Human"
distances.loc[(distances["gaze_to_human"] < thresh) & (distances["gaze_to_ai"] < thresh) & (distances["gaze_to_human"] > distances["gaze_to_ai"]),"Gaze_focus"] = "AI"

distances.to_csv(filepath)

#Plotting section