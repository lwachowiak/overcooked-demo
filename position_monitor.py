import cv2
import csv
import numpy as np
from datetime import datetime
import os

blue_hat_bgr = np.uint8([[[156, 100, 8]]])
green_hat_bgr = np.uint8([[[108, 164, 8]]])

blue_hat_hsv = cv2.cvtColor(blue_hat_bgr, cv2.COLOR_BGR2HSV)
green_hat_hsv = cv2.cvtColor(green_hat_bgr, cv2.COLOR_BGR2HSV)


def annotate_video(video_path, output_filename):
    cap = cv2.VideoCapture(video_path)
    frame_count = 1

    if cap.isOpened() == False:
        print("Error opening video:", video_path)

    with open(output_filename + ".csv", 'w', newline='') as csvfile:

        writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["Human x", "Human y", "Agent x", "Agent y", "Frame number"])
        while cap.isOpened():
            #print("frame " + str(frame_count))

            success, image = cap.read()
            
            if success:

                image_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
                #Use HSV value for overcooked chef's hat in the next two commands
                thresh_blue = cv2.inRange(image_hsv, np.array([90, 100, 100]), np.array([110, 255, 255]))
                thresh_green = cv2.inRange(image_hsv, np.array([70, 100, 100]), np.array([90, 255, 255]))
                contours_b, hierarchy_b = cv2.findContours(thresh_blue, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                contours_g, hierarchy_g = cv2.findContours(thresh_green, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                
                #print(contours_g)
                #print(contours_b)
                
                x_g, y_g, w_g, h_g, x_b, y_b, w_b, h_b = 0, 0, 0, 0, 0, 0, 0, 0

                for cnt in contours_g:
                    x_g, y_g, w_g, h_g = cv2.boundingRect(cnt)

                for cnt_ in contours_b:
                    x_b, y_b, w_b, h_b = cv2.boundingRect(cnt_)

                
                writer.writerow([x_b + w_b/2, y_b + h_b+10, x_g + w_g/2, y_g + h_g+10, frame_count])
                frame_count += 1
            else:
                break;



for i in range(1,36):
    if i<10:
        participant="P0"+str(i)
    else:
        participant="P"+str(i)
    print(participant)
    
    video_path_lvl1="HRI-Experiment-1-Data/"+participant+"/000/world.mp4"
    video_path_lvl2="HRI-Experiment-1-Data/"+participant+"/001/world.mp4"

    print("  lvl1")
    annotate_video(video_path_lvl1, "position_monitor_annotation/"+participant+"_000_monitor")
    print("  lvl2")
    annotate_video(video_path_lvl2, "position_monitor_annotation/"+participant+"_001_monitor")
    

    