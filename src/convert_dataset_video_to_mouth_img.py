import collections
import csv
import os
import sys
from enum import Enum
from pathlib import Path

# adapt paths for jupyter

module_path = os.path.abspath(os.path.join('..'))
if module_path not in sys.path:
    sys.path.append(module_path)

import face_alignment
from yawn_train.src.blazeface_detector import BlazeFaceDetector

import cv2
import dlib
import numpy as np
from imutils import face_utils

from yawn_train.src.ssd_face_detector import SSDFaceDetector

# define one constants, for mouth aspect ratio to indicate open mouth
from yawn_train.src import download_utils, detect_utils, inference_utils
from yawn_train.src.model_config import MOUTH_AR_THRESH, MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT


class ImageResult:
    def __init__(self, is_processed, is_opened_image):
        self.is_processed = is_processed
        self.is_opened_image = is_opened_image

    @staticmethod
    def not_processed():
        return ImageResult(False, False)


class VideoResult:
    def __init__(self, total_frames, dlib_counter, caffe_counter, blazeface_counter, opened_counter, closed_counter):
        self.total_frames = total_frames
        self.dlib_counter = dlib_counter
        self.caffe_counter = caffe_counter
        self.blazeface_counter = blazeface_counter
        self.opened_counter = opened_counter
        self.closed_counter = closed_counter

    @staticmethod
    def empty():
        return VideoResult(0, 0, 0, 0, 0, 0)


class FACE_TYPE(Enum):
    BLAZEFACE = 0
    DLIB = 1
    CAFFE = 2

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_

    def get_next(self):
        val = self.value
        if self.has_value(val + 1):
            return FACE_TYPE(val + 1)
        return FACE_TYPE(0)


class LNDMR_TYPE(Enum):
    DLIB = 0
    FACEALIGN = 1


COLOR_IMG = False
MOUTH_FOLDER = "./mouth_state_new10" + ("_color" if COLOR_IMG else "")
MOUTH_OPENED_FOLDER = os.path.join(MOUTH_FOLDER, 'opened')
MOUTH_CLOSED_FOLDER = os.path.join(MOUTH_FOLDER, 'closed')

TEMP_FOLDER = "./temp"

# https://ieee-dataport.org/open-access/yawdd-yawning-detection-dataset#files
YAWDD_DATASET_FOLDER = "./YawDD dataset"
CSV_STATS = 'video_stat.csv'

read_mouth_open_counter = 0
read_mouth_close_counter = 0

saved_mouth_open_counter = 0
saved_mouth_close_counter = 0

SAMPLE_STEP_IMG_OPENED = 1
SAMPLE_STEP_IMG_CLOSED = 4

(mStart, mEnd) = face_utils.FACIAL_LANDMARKS_IDXS["mouth"]

Path(MOUTH_FOLDER).mkdir(parents=True, exist_ok=True)
Path(MOUTH_OPENED_FOLDER).mkdir(parents=True, exist_ok=True)
Path(MOUTH_CLOSED_FOLDER).mkdir(parents=True, exist_ok=True)

dlib_landmarks_file = download_utils.download_and_unpack_dlib_68_landmarks(TEMP_FOLDER)
# dlib predictor for 68pts, mouth
predictor = dlib.shape_predictor(dlib_landmarks_file)
# initialize dlib's face detector (HOG-based)
detector = dlib.get_frontal_face_detector()

caffe_weights, caffe_config = download_utils.download_caffe(TEMP_FOLDER)
# Reads the network model stored in Caffe framework's format.
face_model = cv2.dnn.readNetFromCaffe(caffe_config, caffe_weights)
ssd_face_detector = SSDFaceDetector(face_model)

import tensorflow as tf

bf_model = download_utils.download_blazeface(TEMP_FOLDER)
blazeface_tf = tf.keras.models.load_model(bf_model, compile=False)
blazefaceDetector = BlazeFaceDetector(blazeface_tf)

# img = cv2.imread(
#     '/Users/igla/Desktop/Screenshot 2021-01-14 at 12.29.25.png', cv2.IMREAD_GRAYSCALE)
# ultrafacedetector = UltraFaceDetector("/Users/igla/Downloads/version-RFB-320_simplified.onnx")

"""
Take mouth ratio only from dlib rect. Use dnn frame for output
"""


def should_process_video(video_name: str) -> bool:
    is_video_sunglasses = video_name.rfind('SunGlasses') != -1
    if is_video_sunglasses:
        # inaccurate landmarks in sunglasses
        print('Video contains sunglasses. Skip', video_name)
        return False

    return video_name.endswith('-Normal.avi') or \
           video_name.endswith('-Talking.avi') or \
           video_name.endswith('-Yawning.avi')


pred_type = collections.namedtuple('prediction_type', ['slice', 'color'])
pred_types = {'face': pred_type(slice(0, 17), (0.682, 0.780, 0.909, 0.5)),
              'eyebrow1': pred_type(slice(17, 22), (1.0, 0.498, 0.055, 0.4)),
              'eyebrow2': pred_type(slice(22, 27), (1.0, 0.498, 0.055, 0.4)),
              'nose': pred_type(slice(27, 31), (0.345, 0.239, 0.443, 0.4)),
              'nostril': pred_type(slice(31, 36), (0.345, 0.239, 0.443, 0.4)),
              'eye1': pred_type(slice(36, 42), (0.596, 0.875, 0.541, 0.3)),
              'eye2': pred_type(slice(42, 48), (0.596, 0.875, 0.541, 0.3)),
              'lips': pred_type(slice(48, 60), (0.596, 0.875, 0.541, 0.3)),
              'teeth': pred_type(slice(60, 68), (0.596, 0.875, 0.541, 0.4))
              }
face_detector = 'sfd'
face_detector_kwargs = {
    "filter_threshold": 0.8
}
fa = face_alignment.FaceAlignment(face_alignment.LandmarksType._3D, flip_input=True, device='cpu',
                                  face_detector=face_detector)


def get_mouth_opened(frame, start_x, start_y, end_x, end_y) -> tuple:
    mouth_shape = predictor(frame, dlib.rectangle(start_x, start_y, end_x, end_y))
    mouth_shape = face_utils.shape_to_np(mouth_shape)
    mouth_arr = mouth_shape[mStart:mEnd]
    mouth_mar_dlib = detect_utils.mouth_aspect_ratio(mouth_arr)
    mouth_mar_dlib = round(mouth_mar_dlib, 2)
    # print(mouth_mar_dlib)

    face_roi_dlib = frame[start_y:end_y, start_x:end_x]
    height_frame, width_frame = face_roi_dlib.shape[:2]
    # swapping the read and green channels
    # https://stackoverflow.com/a/56933474/1461625
    detected_faces = []
    detected_faces.append([0, 0, width_frame, height_frame])
    preds = fa.get_landmarks_from_image(face_roi_dlib, detected_faces)[-1]

    pred_type = pred_types['lips']
    X = preds[pred_type.slice, 0]
    Y = preds[pred_type.slice, 1]
    mouth_shape_3ddfa = []
    for x, y in zip(X, Y):
        mouth_shape_3ddfa.append((x, y))

    # shape = []
    # for idx, pred_type in enumerate(pred_types.values()):
    #     X = preds[pred_type.slice, 0]
    #     Y = preds[pred_type.slice, 1]
    #     for x, y in zip(X, Y):
    #         shape.append((x, y))

    mouth_mar_3ddfa = detect_utils.mouth_aspect_ratio(mouth_shape_3ddfa)
    mouth_mar_3ddfa = round(mouth_mar_3ddfa, 2)
    # print(mouth_mar_3ddfa)

    is_opened_mouth_3ddfa = mouth_mar_3ddfa >= 0.75
    is_opened_mouth_dlib = mouth_mar_dlib >= MOUTH_AR_THRESH

    if is_opened_mouth_3ddfa == is_opened_mouth_dlib:
        return is_opened_mouth_3ddfa, mouth_mar_dlib, LNDMR_TYPE.DLIB  # correct, same as dlib, return dlib ratio
    else:
        return is_opened_mouth_3ddfa, mouth_mar_3ddfa, LNDMR_TYPE.FACEALIGN  # return 3ddfa, as it's more accurate


def recognize_image(video_id: int, video_path: str, frame, frame_id: int, face_type: FACE_TYPE, face_rect_dlib,
                    face_rect_dnn=None) -> ImageResult:
    (start_x, start_y, end_x, end_y) = face_rect_dlib
    start_x = max(start_x, 0)
    start_y = max(start_y, 0)
    if start_x >= end_x or start_y >= end_y:
        print('Invalid detection. Skip', face_rect_dlib)
        return ImageResult.not_processed()

    face_roi_dlib = frame[start_y:end_y, start_x:end_x]
    if face_roi_dlib is None:
        print('Cropped face is None. Skip')
        return ImageResult.not_processed()

    height_frame, width_frame = face_roi_dlib.shape[:2]
    if height_frame < 50 or width_frame < 50:  # some images have invalid dlib face rect
        print('Too small face. Skip')
        return ImageResult.not_processed()

    # https://pyimagesearch.com/wp-content/uploads/2017/04/facial_landmarks_68markup.jpg
    is_mouth_opened, open_mouth_ratio, lndmk_type = get_mouth_opened(frame, start_x, start_y, end_x, end_y)

    # skip frames in normal and talking, containing opened mouth (we detect only yawn)
    video_name = os.path.basename(video_path)
    is_video_no_yawn = video_name.endswith('-Normal.avi') or \
                       video_name.endswith('-Talking.avi')
    if is_mouth_opened and is_video_no_yawn:
        # some videos may contain opened mouth, skip these situations
        return ImageResult.not_processed()

    prefix = 'dlib'
    target_face_roi = None
    if face_rect_dnn is not None:
        (start_x, start_y, end_x, end_y) = face_rect_dnn
        start_x = max(start_x, 0)
        start_y = max(start_y, 0)
        if start_x < end_x and start_y < end_y:
            face_roi_dnn = frame[start_y:end_y, start_x:end_x]
            target_face_roi = face_roi_dnn
            prefix = face_type.name.lower()

    if target_face_roi is None:
        target_face_roi = face_roi_dlib

    if len(frame.shape) == 2 or COLOR_IMG:  # single channel
        gray_img = target_face_roi
    else:
        gray_img = cv2.cvtColor(target_face_roi, cv2.COLOR_BGR2GRAY)
    gray_img = detect_utils.resize_img(gray_img, MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT)

    lndmk_type_name = lndmk_type.name.lower()
    if is_mouth_opened:
        global read_mouth_open_counter
        read_mouth_open_counter = read_mouth_open_counter + 1
        # reduce img count
        if read_mouth_open_counter % SAMPLE_STEP_IMG_OPENED != 0:
            return ImageResult.not_processed()

        global saved_mouth_open_counter
        saved_mouth_open_counter = saved_mouth_open_counter + 1
        file_name = os.path.join(MOUTH_OPENED_FOLDER,
                                 f'{read_mouth_open_counter}_{open_mouth_ratio}_{video_id}_{frame_id}_{prefix}_{lndmk_type_name}.jpg')
        cv2.imwrite(file_name, gray_img)
        return ImageResult(is_processed=True, is_opened_image=True)
    else:
        global read_mouth_close_counter
        read_mouth_close_counter = read_mouth_close_counter + 1
        # reduce img count
        if read_mouth_close_counter % SAMPLE_STEP_IMG_CLOSED != 0:
            return ImageResult.not_processed()

        global saved_mouth_close_counter
        saved_mouth_close_counter = saved_mouth_close_counter + 1
        file_name = os.path.join(MOUTH_CLOSED_FOLDER,
                                 f'{read_mouth_close_counter}_{open_mouth_ratio}_{video_id}_{frame_id}_{prefix}_{lndmk_type_name}.jpg')
        cv2.imwrite(file_name, gray_img)
        return ImageResult(is_processed=True, is_opened_image=False)


def detect_faces_complex(frame):
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    face_list_dlib = inference_utils.detect_face_dlib(detector, gray_frame)
    if len(face_list_dlib) > 0:
        return face_list_dlib, FACE_TYPE.DLIB

    face_list_dnn_cafe = ssd_face_detector.detect_face(frame)
    if len(face_list_dnn_cafe) > 0:
        return face_list_dnn_cafe, FACE_TYPE.CAFFE

    face_list_dnn_blaze = blazefaceDetector.detect_face(frame)
    if len(face_list_dnn_blaze) > 0:
        return face_list_dnn_blaze, FACE_TYPE.BLAZEFACE
    return [], None


def process_video(video_id, video_path) -> VideoResult:
    video_name = os.path.basename(video_path)
    if should_process_video(video_name) is False:
        print('Video should not be processed', video_path)
        return VideoResult.empty()

    cap = cv2.VideoCapture(video_path)
    if cap.isOpened() is False:
        print('Video is not opened', video_path)
        return VideoResult.empty()
    face_dlib_counter = 0
    face_caffe_counter = 0
    face_blazeface_counter = 0

    opened_img_counter = 0
    closed_img_counter = 0

    frame_id = 0
    face_type = FACE_TYPE.DLIB
    while True:
        ret, frame = cap.read()
        if ret is False:
            break
        if frame is None:
            print('No images left in', video_path)
            break
        if np.shape(frame) == ():
            print('Empty image. Skip')
            continue

        frame_id = frame_id + 1

        face_list, f_type = detect_faces_complex(frame)
        if len(face_list) == 0:
            # skip images not recognized by dlib or other detectors
            continue

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        recognize_frame = frame if COLOR_IMG else gray_frame
        if face_type == FACE_TYPE.DLIB:
            image_result = recognize_image(video_id, video_path, recognize_frame, frame_id, face_type,
                                           face_list[0])
            is_processed = image_result.is_processed
            if is_processed:
                face_type = face_type.get_next()
                face_dlib_counter = face_dlib_counter + 1
                if image_result.is_opened_image:
                    opened_img_counter = opened_img_counter + 1
                else:
                    closed_img_counter = closed_img_counter + 1
            continue

        if face_type == FACE_TYPE.CAFFE:
            face_list_dnn = ssd_face_detector.detect_face(frame)
            if len(face_list_dnn) == 0:
                face_type = face_type.get_next()
                print('Face not found with Caffe DNN')
                continue

            image_result = recognize_image(video_id, video_path, recognize_frame, frame_id, face_type,
                                           face_list[0],
                                           face_list_dnn[0])
            is_processed = image_result.is_processed
            if is_processed:
                face_type = face_type.get_next()
                face_caffe_counter = face_caffe_counter + 1
                if image_result.is_opened_image:
                    opened_img_counter = opened_img_counter + 1
                else:
                    closed_img_counter = closed_img_counter + 1

        if face_type == FACE_TYPE.BLAZEFACE:
            face_list_dnn = blazefaceDetector.detect_face(frame)
            if len(face_list_dnn) == 0:
                face_type = face_type.get_next()
                print('Face not found with Blazeface')
                continue
            image_result = recognize_image(video_id, video_path, recognize_frame, frame_id, face_type,
                                           face_list[0],
                                           face_list_dnn[0])
            is_processed = image_result.is_processed
            if is_processed:
                face_type = face_type.get_next()
                face_blazeface_counter = face_blazeface_counter + 1
                if image_result.is_opened_image:
                    opened_img_counter = opened_img_counter + 1
                else:
                    closed_img_counter = closed_img_counter + 1

    print(
        f"Total images: {face_dlib_counter + face_caffe_counter + face_blazeface_counter}"
        f', dlib: {face_dlib_counter} images'
        f', blazeface: {face_blazeface_counter} images'
        f', caffe: {face_caffe_counter} images in video {video_name}'
    )
    cap.release()

    # The function is not implemented. Rebuild the library with Windows, GTK+ 2.x or Cocoa support. If you are on
    # Ubuntu or Debian, install libgtk2.0-dev and pkg-config, then re-run cmake or configure script in function
    # 'cvDestroyAllWindows'
    try:
        cv2.destroyAllWindows()
    except:
        print('No destroy windows')

    return VideoResult(
        frame_id,
        face_dlib_counter,
        face_blazeface_counter,
        face_caffe_counter,
        opened_img_counter,
        closed_img_counter
    )


def write_csv_stat(filename, video_count, video_result: VideoResult):
    video_stat_dict_path = os.path.join(MOUTH_FOLDER, CSV_STATS)
    if os.path.isfile(video_stat_dict_path) is False:
        with open(video_stat_dict_path, 'w') as f:
            w = csv.writer(f)
            w.writerow(['Video id', 'File name', 'Total frames', 'Image saved', 'Opened img', 'Closed img'])

    # mode 'a' append
    with open(video_stat_dict_path, 'a') as f:
        w = csv.writer(f)
        img_counter = video_result.caffe_counter + video_result.dlib_counter + video_result.blazeface_counter
        w.writerow((
            video_count,
            filename,
            video_result.total_frames,
            img_counter,
            video_result.opened_counter,
            video_result.closed_counter
        ))


def process_videos():
    video_count = 0
    total_frames = 0
    for root, dirs, files in os.walk(YAWDD_DATASET_FOLDER):
        for file in files:
            if file.endswith(".avi"):
                video_count = video_count + 1
                file_name = os.path.join(root, file)
                print('Current video', file_name)

                video_result = process_video(video_count, file_name)
                total_frames = total_frames + video_result.total_frames
                write_csv_stat(file_name, video_count, video_result)

    print(f'Videos processed: {video_count}')
    print(f'Total read images: {total_frames}')
    print(f'Total saved images: {saved_mouth_open_counter + saved_mouth_close_counter}')
    print(f'Saved opened mouth images: {saved_mouth_open_counter}')
    print(f'Saved closed mouth images: {saved_mouth_close_counter}')


if __name__ == '__main__':
    process_videos()
