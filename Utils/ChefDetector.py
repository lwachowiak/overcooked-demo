import cv2
import numpy as np

cap = cv2.VideoCapture("/home/peter/recordings/2022_03_03/P01/000/world.mp4")
frame_count = 0

blue_chef = cv2.imread("/home/peter/Pictures/bluechef")
green_chef = cv2.imread("/home/peter/Pictures/greenchef")

w_b = blue_chef.shape[1]
h_b = blue_chef.shape[0]

w_g = green_chef.shape[1]
h_g = green_chef.shape[0]

if cap.isOpened() == False:
    print("Error opening video")

while cap.isOpened():

    success, image = cap.read()
        
    if success and frame_count > 35:

        blue_find = cv2.matchTemplate(image, blue_chef, method=cv2.TM_CCOEFF_NORMED)
        green_find = cv2.matchTemplate(image, green_chef, method=cv2.TM_CCOEFF_NORMED)

        _, blue_conf, _, blue_loc = cv2.minMaxLoc(blue_find)

        _, green_conf, _, green_loc = cv2.minMaxLoc(green_find)

        draw1 = cv2.rectangle(image, blue_loc, (blue_loc[0] + w_b, blue_loc[1] + h_b), color=(0,255,0), thickness=3) if blue_conf > 0.8 else None
        draw1 = cv2.rectangle(image, green_loc, (green_loc[0] + w_g, green_loc[1] + h_g), color=(0,0,255), thickness=3) if green_conf > 0.8 else None

        cv2.imshow("Frame", image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    elif frame_count <= 35:
        frame_count += 1
    else:
        exit()
