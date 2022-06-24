
import cv2
import numpy as np
from PyQt6.QtCore import Qt, QRect, QLine, QPoint, QSize
from PyQt6.QtGui import QImage
import copy
from bbox import BBox

class ObjectTracker:
    def __init__(self):

        #only choose one type of tracker

        #self.tracker = cv2.TrackerKCF_create()  # bad
        #self.tracker = cv2.TrackerGOTURN_create()  # not very good, requires NN (slow)
        #self.tracker = cv2.TrackerMIL_create()  # good but slow
        #self.tracker = cv2.TrackerBoosting_create()  # good, but HELLA SLOW
        #self.tracker = cv2.TrackerTLD_create()  # fast, but hops around a lot

        #self.tracker = cv2.TrackerMOSSE_create()   # reasonable accuracy, fast
        self.tracker = cv2.TrackerMedianFlow_create()  # good, and fast - Best for this app
        #self.tracker = cv2.TrackerCSRT_create()    # very good accuracy, not fast

    def QImage2cvMat(self, image):  # (QImage image)
        mat = None  # cv2.Mat

        image = image.scaled(QSize(800,600))

        img_frm = image.format()

        height = image.height()
        width = image.width()
        bytecount = image.byteCount()

        ptr = image.bits()
        ptr.setsize(bytecount)
        mat = np.array(ptr).reshape(height, width, 3)
        mat = cv2.cvtColor(mat, cv2.COLOR_BGR2RGB)

        return mat;

    def predict_bbox(self, prevQImg, newQImg, bbox):

        # create opencv Mat imgs from PyQt QImages
        prevMatImg = self.QImage2cvMat(prevQImg)
        newMatImg = self.QImage2cvMat(newQImg)

        # create opencv rectangle from bbox
        bbox.align_corners()   # for inverted rectangles, make sure bbox corners are aligned
        x = bbox.ul.x()
        y = bbox.ul.y()
        w =  abs(bbox.lr.x() - bbox.ul.x())
        h = abs(bbox.lr.y() - bbox.ul.y())

        # initialize tracker with rectangle and predict new bbox
        self.tracker.init(prevMatImg,(x,y,w,h))
        ok, new_box = self.tracker.update(newMatImg)

        if ok:
            new_x1 = int(new_box[0])
            new_y1 = int(new_box[1])
            new_x2 = int(new_box[0] + new_box[2])
            new_y2 = int(new_box[1] + new_box[3])

            qp_ul = QPoint(new_x1,new_y1)
            qp_lr = QPoint(new_x2,new_y2)

            # create new bbox with prediction
            new_bbox = copy.deepcopy(bbox)

            new_bbox.setTopLeft(qp_ul)
            new_bbox.setBottomRight(qp_lr)
        else:
            # if tracking not successful, create deep copy of original bbox
            new_bbox = copy.deepcopy(bbox)

        return new_bbox