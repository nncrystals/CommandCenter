import math
import random

import cv2
import numpy as np

from inference_service_proto import inference_service_pb2 as grpc_def


def render_inference(image_buf, detections: grpc_def.ResultPerImage, alpha=0.4):
    img_buf = np.asarray(bytearray(image_buf), dtype="uint8")
    im = cv2.imdecode(img_buf, cv2.IMREAD_COLOR)
    detected_objects = detections

    mask_channel = np.zeros([im.shape[0], im.shape[1]], dtype=bool)
    overlay = np.zeros_like(im)
    for d in detected_objects:
        m = d.mask
        m.dtype = bool
        mask_channel[m] = True
        overlay[m] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

    # apply overlay
    im[mask_channel] = im[mask_channel] * (1 - alpha) + overlay[mask_channel] * alpha

    for d in detected_objects:
        b = d.bbox
        l = d.label
        s = d.score

        b = [math.ceil(coor) for coor in b]
        pt1 = (b[0], b[1])
        pt2 = (b[2], b[3])

        cv2.rectangle(im, pt1, pt2, (255, 0, 0), thickness=1)
        cv2.putText(im, f"{l} {s:.2f}", pt1, cv2.FONT_HERSHEY_PLAIN, 1, (255, 0, 0))
    return im
