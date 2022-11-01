import cv2
import csv
import numpy as np

blue_hat_bgr = np.uint8([[[74, 54, 25]]])
green_hat_bgr = np.uint8([[[41, 103, 35]]])

blue_hat_hsv = cv2.cvtColor(blue_hat_bgr, cv2.COLOR_BGR2HSV)
green_hat_hsv = cv2.cvtColor(green_hat_bgr, cv2.COLOR_BGR2HSV)
#print(blue_hat_hsv)
#print(green_hat_hsv)

###########################################  COLORS TO TUNE  #######################################################

blue_low = np.array([70, 130, 50])
blue_high = np.array([110, 255, 143])
 
green_low = np.array([50, 60, 100])
green_high = np.array([80, 170, 140])

####################################################################################################################
video_res = (1280, 720)
fourcc = cv2.VideoWriter_fourcc(*'MP4V')

cap = cv2.VideoCapture("/home/peter/HRI-experiment-1-data/P03/000/world.mp4")
writer = cv2.VideoWriter("/home/peter/Desktop/agents.mp4", fourcc, 12, video_res)  

frame_count = 0

x_g, y_g, w_g, h_g, x_b, y_b, w_b, h_b = 0, 0, 0, 0, 0, 0, 0, 0

if cap.isOpened() == False:
    print("Error opening video")

while cap.isOpened():

    success, image = cap.read()
        
    if success and frame_count > 0:
        
        image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        mask_blue = cv2.inRange(image, blue_low, blue_high)
        mask_green = cv2.inRange(image, green_low, green_high)

        # out1 = cv2.bitwise_and(image, image, mask=mask_blue)
        # out2 = cv2.bitwise_and(image, image, mask=mask_green)

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

        image = cv2.cvtColor(image, cv2.COLOR_HSV2BGR)

        cv2.rectangle(image, (int(x_g), int(y_g)), (int(x_g + w_g), int(y_g + h_g)), (0,0, 255), 2)
        cv2.rectangle(image, (int(x_b), int(y_b)), (int(x_b + w_b), int(y_b + h_b)), (255,0,0), 2)
        
        
        # cv2.imshow("Frame " + str(frame_count), image)
        # cv2.waitKey(0) 
        # cv2.destroyAllWindows()

        writer.write(image)
        
        frame_count += 1
    elif frame_count <= 0:
        frame_count += 1
    else:
        cap.release()
        writer.release()
        cv2.destroyAllWindows()
        exit()
