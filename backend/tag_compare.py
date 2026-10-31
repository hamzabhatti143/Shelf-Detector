import re
import sys

import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR

im = cv2.imread(sys.argv[1])
ocr = RapidOCR()
tags = [(216,556,450,633),(1070,579,1294,656),(1502,607,1699,678),(1909,626,2102,696),
        (0,1022,191,1096),(294,1029,525,1097),(547,1035,657,1102),(773,1029,988,1099),
        (1038,1036,1245,1112),(1431,1043,1632,1110)]
orph = [(1825,1053,1874,1096),(2044,1052,2100,1102)]


def crop(b, m):
    x1, y1, x2, y2 = b
    w, h = x2 - x1, y2 - y1
    return im[max(0, int(y1 - h * m)):int(y2 + h * m), max(0, int(x1 - w * m)):int(x2 + w * m)]


def prep(c, minh):
    h = c.shape[0]
    if minh and h < minh:
        c = cv2.resize(c, None, fx=minh / h, fy=minh / h, interpolation=cv2.INTER_CUBIC)
    return cv2.copyMakeBorder(c, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=(255, 255, 255))


def tallest(r):
    num = [z for z in (r or []) if any(ch.isdigit() for ch in z[1])]
    return max(num, key=lambda z: z[0][2][1] - z[0][0][1])[1] if num else ""


for name, items, m in [("TAG", tags, 0.05), ("ORPHAN", orph, 0.25)]:
    for minh in (96, 0):
        out = [tallest(ocr(prep(crop(b, m), minh))[0]) for b in items]
        print(name, "minh", minh, out)