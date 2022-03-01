import cv2
import csv
import numpy as np
from datetime import datetime

blue_hat_bgr = np.uint8([[[156, 100, 8]]])
green_hat_bgr = np.uint8([[[108, 164, 8]]])

blue_hat_hsv = cv2.cvtColor(blue_hat_bgr, cv2.COLOR_BGR2HSV)
green_hat_hsv = cv2.cvtColor(green_hat_bgr, cv2.COLOR_BGR2HSV)
#print(blue_hat_hsv)
#print(green_hat_hsv)

cap = cv2.VideoCapture("/home/peter/recordings/2022_03_01/002/world.mp4")
frame_count = 0

if cap.isOpened() == False:
    print("Error opening video")

with open(str(datetime.now()) + ".csv", 'w', newline='') as csvfile:

    writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["Human X", "Human y", "Agent x", "Agent y"])
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
            
            for cnt in contours_g:
                x_g, y_g, w_g, h_g = cv2.boundingRect(cnt)

            for cnt_ in contours_b:
                x_b, y_b, w_b, h_b = cv2.boundingRect(cnt_)

            
            writer.writerow([x_b + w_b/2, y_b + h_b, x_g + w_g/2, y_g + h_g, frame_count])
            frame_count += 1
        else:
            exit()
    