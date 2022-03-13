import cv2
import csv
import numpy as np
import os

blue_hat_bgr = np.uint8([[[156, 100, 8]]])
green_hat_bgr = np.uint8([[[108, 164, 8]]])

blue_hat_hsv = cv2.cvtColor(blue_hat_bgr, cv2.COLOR_BGR2HSV)
green_hat_hsv = cv2.cvtColor(green_hat_bgr, cv2.COLOR_BGR2HSV)


def annotate_video(video_path, output_filename):
        ###########################################  COLORS TO TUNE  #######################################################

    blue_low = np.array([50, 0, 0])
    blue_high = np.array([80, 60, 60])

    green_low = np.array([20, 80, 0])
    green_high = np.array([60, 100, 50])

    ####################################################################################################################
    video_res = (1280, 720)
    fourcc = cv2.VideoWriter_fourcc(*'MP4V')

    cap = cv2.VideoCapture(video_path)
    video_writer = cv2.VideoWriter(output_filename + ".mp4", fourcc, 12.0, video_res)

    frame_count = 0
    x_g, y_g, w_g, h_g, x_b, y_b, w_b, h_b = 0, 0, 0, 0, 0, 0, 0, 0

    if cap.isOpened() == False:
        print("Error opening video")

    with open(output_filename + ".csv", 'w', newline='') as csvfile:

        writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["Human x", "Human y", "Agent x", "Agent y", "Frame number"])
        while cap.isOpened():
            #print("frame " + str(frame_count))

            success, image = cap.read()
            
            if success:

                mask_blue = cv2.inRange(image, blue_low, blue_high)
                mask_green = cv2.inRange(image, green_low, green_high)

                ret_blue, thresh_blue = cv2.threshold(mask_blue, 40, 255, 0)
                ret_green, thresh_green = cv2.threshold(mask_green, 40, 255, 0)
            
                contours_b, hierarchy_b = cv2.findContours(thresh_blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                contours_g, hierarchy_g = cv2.findContours(thresh_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            
                max_blue_cont = sorted(contours_b, key=cv2.contourArea) if len(contours_b) !=0 else None
                max_green_cont = sorted(contours_g, key=cv2.contourArea) if len(contours_g) != 0 else None
                
                if max_blue_cont is not None:
                    x_b, y_b, w_b, h_b = cv2.boundingRect(max_blue_cont[-1])

                if max_green_cont is not None:
                    x_g, y_g, w_g, h_g = cv2.boundingRect(max_green_cont[-1])
                
                writer.writerow([x_b + w_b/2, y_b + h_b, x_g + w_g/2, y_g + h_g, frame_count])

                cv2.rectangle(image, (int(x_g), int(y_g)), (int(x_g + w_g), int(y_g + h_g)), (0,0, 255), 2)
                cv2.rectangle(image, (int(x_b), int(y_b)), (int(x_b + w_b), int(y_b + h_b)), (255,0,0), 2)

                video_writer.write(image)
                frame_count += 1
            else:
                cap.release()
                video_writer.release()
                cv2.destroyAllWindows()
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
    annotate_video(video_path=video_path_lvl1, output_filename="position_monitor_annotation/"+participant+"_000_monitor")
    print("  lvl2")
    annotate_video(video_path=video_path_lvl2, output_filename="position_monitor_annotation/"+participant+"_001_monitor")
    

    