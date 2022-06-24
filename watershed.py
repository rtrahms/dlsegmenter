from PyQt6.QtCore import Qt, QRect, QLine, QPoint, QSize
from PyQt6.QtGui import QImage, QPixmap

import cv2
import numpy as np
from matplotlib import cm

class Watershed:
    def __init__(self):

        self.watershed_img_width = 800
        self.watershed_img_height = 600

        return

    # def createColormap(self, color_map="tab20"):
    #     color_map_func = getattr(cm, color_map)
    #     return [tuple(map(lambda x: x * 255, color_map_func(i)[:3])) for i in range(20)]

    def QImage2cvMat(self, image, channels):  # (QImage image)

        image = image.scaled(QSize(self.watershed_img_width,self.watershed_img_height))

        height = image.height()
        width = image.width()
        #bytecount = image.byteCount()
        bytecount = height*width*channels

        ptr = image.bits()
        ptr.setsize(bytecount)
        mat = np.array(ptr).reshape(height, width, channels)
        return mat;

    def CvMat2QImage(self,inputMat, channels):
        if channels == 4:
            qim = QImage(inputMat.data,inputMat.shape[1],inputMat.shape[0],inputMat.strides[0],QImage.Format.Format_RGBA8888)
        else:  # channels = 3
            qim = QImage(inputMat.data,inputMat.shape[1],inputMat.shape[0],inputMat.strides[0],QImage.Format.Format_RGB888)
        return qim

    def convertMatRGBC3to32S(self, src_mat, dst_mat):
        height = src_mat.shape[0]
        width = src_mat.shape[1]

        num_arrays = src_mat.shape[-1]

        # super efficient
        [R, G, B, A] = np.dsplit(src_mat,num_arrays)
        R = np.reshape(R,(height,width)).astype(dtype=np.int32)
        R = np.left_shift(R, 16)
        G = np.reshape(G,(height, width)).astype(dtype=np.int32)
        G = np.left_shift(G, 8)
        B = np.reshape(B,(height,width)).astype(dtype=np.int32)

        # dst_mat = R + G + B (element-wise add)
        interim = np.add(R,G)
        dst_mat = np.add(interim,B)

        # works correctly, but VERY SLOW
        # for h in range(height):
        #      for w in range(width):
        #              dst_mat[h][w] = R[h][w] + G[h][w] + B[h][w]

        return dst_mat

    def convertMat32StoRGBC3(self, src_mat, dst_mat):
        height = src_mat.shape[0]
        width = src_mat.shape[1]

        # make a src filter for the conversion (1 and 0 values)
        src_array = np.array(src_mat)
        src_filter = src_array > 0
        src_filter = src_filter.astype(np.uint8)
        src_filter = np.reshape(src_filter,(height,width, 1))

        # uncompress RGB channels and store

        # super-efficient
        R = np.right_shift(src_mat,16)
        R = np.bitwise_and(R, 0xff)
        R = np.reshape(R, (height,width,1)).astype(np.uint8)

        G = np.right_shift(src_mat,8)
        G = np.bitwise_and(G,0xff)
        G = np.reshape(G,(height,width,1)).astype(np.uint8)

        B = np.bitwise_and(src_mat,0xff)
        B = np.reshape(B, (height,width,1)).astype(np.uint8)

        dst_mat = np.concatenate((R,G,B),axis=2)
        dst_filter = np.concatenate((src_filter, src_filter, src_filter), axis=2)

        # apply filter to result
        dst_mat = dst_mat*dst_filter

        # works correctly, but VERY SLOW
        # for h in range(height):
        #     for w in range(width):
        #         label = src_mat[h][w]
        #         if label > 0:
        #             dst_mat[h][w][0] = R[h][w]
        #             dst_mat[h][w][1] = G[h][w]
        #             dst_mat[h][w][2] = B[h][w]

        return dst_mat

    def process(self, input_img, overlay_img):

        # make a copy of input image for processing
        img_copy = input_img.copy()
        input_mat = self.QImage2cvMat(img_copy, 3)

        overlay_img_copy = overlay_img.copy()
        overlay_mat = self.QImage2cvMat(overlay_img_copy.toImage(), 4)

        #overlay_mat2 = cv2.cvtColor(overlay_mat,cv2.COLOR_BGRA2GRAY)

        # debug only - write something on the cv Mat object
        #overlay_mat = cv2.putText(overlay_mat,"Watershed processed",(500,575),cv2.FONT_HERSHEY_SIMPLEX,0.5,(255,255,0,255),2,cv2.LINE_AA)

        # debug - show input and overlay mats
        #cv2.imshow("input_mat", input_mat)
        #cv2.imshow("overlay_mat", overlay_mat)

        # convert to 3-channel RGB
        input2 = cv2.cvtColor(input_mat, cv2.COLOR_BGRA2RGB)
        input_img_copy = input2.copy()
        input_img_copy = input_img_copy.astype(np.uint8)

        #input3 = cv2.cvtColor(input_mat,cv2.COLOR_BGRA2GRAY)

        # compress into 1-channel (32-bit) marker image
        marker_image_copy = np.zeros(overlay_mat.shape[:2], dtype=np.int32)
        marker_image_copy = self.convertMatRGBC3to32S(overlay_mat, marker_image_copy)

        # test loopback - uncompress back to 3-channel RGB and display
        #test_output = np.zeros(input_img_copy.shape, dtype=np.uint8)
        #self.convertMat32StoRGBC3(marker_image_copy,test_output)
        #cv2.imshow("test_output", test_output)

        # perform watershed and generate 3-channel segment mask
        cv2.watershed(input_img_copy, marker_image_copy)
        segments = np.zeros(input_img_copy.shape, dtype = np.uint8)
        segments = self.convertMat32StoRGBC3(marker_image_copy, segments)

        segments2 = cv2.cvtColor(segments,cv2.COLOR_RGB2GRAY)
        #cv2.imshow("segments2", segments2)

        # convert segment mask back to 4-channel
        segments = cv2.cvtColor(segments,cv2.COLOR_RGB2BGRA)

        # convert back to QImage and then to QPixmap
        result_img = self.CvMat2QImage(segments, 4)
        result_pixmap = QPixmap.fromImage(result_img)

        # scale back to original image size
        result_pixmap = result_pixmap.scaled(QSize(input_img.width(),input_img.height()))

        return result_pixmap

    def clear(self):
        self.result_img = None
        self.valid = False
        return

    def draw(self, qp):
        if self.valid == False:
            return

        # TODO: draw mask image
        return
