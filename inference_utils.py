import cv2
import numpy as np


def prepare_image(image_frame, image_size):
    image_frame = cv2.resize(image_frame, image_size, cv2.INTER_AREA)
    image_frame = cv2.cvtColor(image_frame, cv2.COLOR_BGR2GRAY)
    return image_frame[:, :, np.newaxis]  # expand 1 dimension