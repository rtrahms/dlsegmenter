import os

from PyQt6.QtCore import QDir, Qt, QSize, QRect, QPoint
from PyQt6 import QtWidgets, QtCore, QtGui, uic
from PyQt6.QtGui import QImage, QPainter, QPalette, QPixmap, QBrush, QPen, QImageWriter

import copy
from watershed import Watershed
from obj_label import ObjectLabel
from markup import Markup
import cv2

class GT:
    def __init__(self):

        self.image_filename = "image.jpg"
        self.mask_filename = "image_mask.jpg"
        self.markup_filename = "image_markup.txt"
        self.markup_image_filename = "image_markup.jpg"

        self.image_width = 0
        self.image_height = 0
        self.markup_list = []

        self.pane_width = 0
        self.pane_height = 0

        self.mask_image = None
        self.watershed = Watershed()

    def set_mask_filename(self, image_filename):

        # save image filename for reference
        self.image_filename = image_filename

        image_prefix = os.path.splitext(image_filename)[0]

        self.mask_filename = image_prefix + "_mask.jpg"
        #print("image filename = " + self.image_filename + " mask filename = " + self.mask_filename)

        self.markup_filename = image_prefix + "_markup.txt"
        self.markup_image_filename = image_prefix + "_markup.jpg"

        return

    def set_img_dims(self, src_img, img_width, img_height):
        self.image_width = img_width
        self.image_height = img_height

    def set_disp_dims(self, disp_width, disp_height):
        self.pane_width = disp_width
        self.pane_height = disp_height

        for mu in self.markup_list:
            mu.setDisplayDims(self.pane_width, self.pane_height)

    def add(self, markup):
        self.markup_list.append(markup)
        return True

    def remove_selected_markups(self, x, y, brush_size):
        x_scale = float(self.image_width / self.pane_width)
        y_scale = float(self.image_height / self.pane_height)
        native_x = x * x_scale
        native_y = y * y_scale
        native_brush_size = x_scale * brush_size

        # inclusion bounds
        x_min = native_x - native_brush_size/2
        x_max = native_x + native_brush_size/2
        y_min = native_y - native_brush_size/2
        y_max = native_y + native_brush_size/2

        for mu in self.markup_list:
            if mu.contains_point(x_min, x_max, y_min, y_max) == True:
                self.markup_list.remove(mu)
        return

    def remove(self,markup):
        if markup != None:
            self.bbox_list.remove(markup)

    def load_from_file(self, load_gt_dir_path):

        # attempt to load mask image from file
        full_path_mask_filename = load_gt_dir_path + "/" + self.mask_filename
        #print("full path of mask file to load: " + full_path_filename)

        if os.path.exists(full_path_mask_filename) == True:
            # read and scale pixmap overlay from file
            self.mask_image = QPixmap(full_path_mask_filename)
            # input_pixmap = QPixmap(full_path_mask_filename)
            # self.mask_image = input_pixmap.scaled(QSize(self.pane_width,self.pane_height))
        else:
            self.mask_image = None

        # attempt to load any stored markups
        full_path_markup_filename = load_gt_dir_path + "/" + self.markup_filename
        if os.path.exists(full_path_markup_filename) == True:
            fp = open(full_path_markup_filename)
            lines = fp.readlines()
            fp.close()

            for l in lines:
                # strip newline and split line into elements
                curr_list = l.rstrip().split(',')
                class_name = curr_list[0]
                cx = int(curr_list[1])
                cy = int(curr_list[2])
                brush_size = float(curr_list[3])
                class_color = curr_list[4]
                cl = ObjectLabel()
                cl.name = class_name
                cl.color = class_color

                # scale each markup from native img dims
                mu = Markup(self.image_width, self.image_height, self.pane_width, self.pane_height)
                mu.setNativePoint(cx,cy,brush_size,cl)

                self.markup_list.append(mu)

        return self.mask_image

    def save_to_file(self, save_gt_dir_path):

        if self.mask_image == None:
            return

        full_path_mask_filename = save_gt_dir_path + "/" + self.mask_filename
        #print("full path of mask file to save: " + full_path_filename)

        # Scale pixmap to proper image dimensions
        output_pixmap = QPixmap.scaled(self.mask_image,QSize(self.image_width,self.image_height))

        # QPixmap save to file
        output_pixmap.save(full_path_mask_filename,"JPG")

        # save all markups
        full_path_markup_filename = save_gt_dir_path + "/" + self.markup_filename

        mu_filestream = open(full_path_markup_filename,"w")
        for mu in self.markup_list:

            new_string = mu.class_label.name + "," + str(mu.cx) + "," + str(mu.cy) + "," + str(mu.brush_size) + "," + mu.class_label.color + "\n"
            mu_filestream.write(new_string)
        mu_filestream.close()

        return

    def set_overlay_mask(self, mask_image):
        self.mask_image = mask_image.copy()
        return

    def set_markup_image(self,markup_image):
        self.markup_image = markup_image.copy()
        return

    def delete_mask(self):
        self.mask_image = None
        return

    def delete_all_markups(self):
        self.markup_list.clear()

    def num_markups(self):
        return len(self.markup_list)


    def predict_annotation(self, src_gt, prev_img, next_img):
        self.markup_list = []

        # copy active markups from src_gt
        for mu in src_gt.markup_list:
                # nothing fancy - copy markup from src gt
                new_mu = copy.deepcopy(mu)

                # add markup to list
                self.markup_list.append(new_mu)

        # copy mask overlay from src_gt
        if src_gt.mask_image != None:
            self.mask_image = src_gt.mask_image.copy()
        else:
            self.mask_image = None

    def get_overlay_mask(self):
        if self.mask_image == None:
            self.mask_image = QPixmap(self.pane_width, self.pane_height)
            self.mask_image.fill(Qt.transparent)

        return self.mask_image

    def process_mask(self, qpainter, src_img, markup_img, watershed_process):

        # save current opacity
        curr_opacity = qpainter.opacity()

        # first, draw any current masks & markups on overlay
        qpainter.setOpacity(1.0)
        #self.draw(qpainter)

        # draw all markups only, no masks
        for mu in self.markup_list:
            mu.draw(qpainter)

        # if watershed processing, pass both the source image and the mask in
        if watershed_process == True:
            self.mask_image = self.watershed.process(src_img, markup_img)
        else:
            # store a combined copy of everything drawn so far
            self.mask_image = markup_img.copy()

        # restore original opacity
        qpainter.setOpacity(curr_opacity)

    def draw_mask_and_markups(self, qpainter, show_mask):
        #print("markup list size = " + str(len(self.markup_list)))

        # draw current mask (if it exists)
        if self.mask_image != None and show_mask == True:
            mask_pixmap = self.mask_image.scaled(QSize(self.pane_width,self.pane_height))

            #qpainter.drawPixmap(0, 0, self.mask_image)
            qpainter.drawPixmap(0, 0, mask_pixmap)

        # draw all markups on top of mask
        for mu in self.markup_list:
            mu.draw(qpainter)

        return
