from PyQt6.QtCore import QDir, Qt, QSize, QRect, QPoint, QThread, QTimer, QUrl
from PyQt6 import QtWidgets, QtCore, QtGui, uic
from PyQt6.QtGui import QImage, QPainter, QPalette, QPixmap, QBrush, QPen, QDesktopServices
from PyQt6.QtWidgets import (QApplication, QFileDialog, QLabel,
        QMainWindow, QGraphicsView, QMenu, QMessageBox, QScrollArea, QSizePolicy,
        QWidget, QStackedWidget)
import yaml
from yaml import FullLoader, Dumper

import pyautogui

import glob
import sys, os

from obj_label import ObjectLabel
from gt import GT
from markup import Markup
from zoom_ctrl import ZoomControl
from help import HelpDialog
from setup import SetupDialog
from logger import Logger


class GT_Load_Process(QThread):
    def __init__(self):
        QThread.__init__(self)

        self.num_processed = 0
        self.img_file_list = []
        self.gt_list = []

    def __del__(self):
        self.wait()

    def check_progress(self):
        return self.num_processed

    def load_params(self, img_file_list, gt_list):

        self.img_file_list = img_file_list
        self.gt_list = gt_list

    def run(self):

        self.num_processed = 0

        for img_path in self.img_file_list:
            new_gt = GT()
            image_filename = os.path.basename(img_path)
            new_gt.set_mask_filename(image_filename)
            self.gt_list.append(new_gt)

            self.num_processed += 1

        print("gt load thread complete.")

        return

class GT_Save_Process(QThread):
    def __init__(self):
        QThread.__init__(self)

        self.num_processed = 0
        self.save_path = "unknown"
        self.gt_list = []

    def __del__(self):
        self.wait()

    def check_progress(self):
        return self.num_processed

    def load_params(self,save_path, gt_list):
        self.save_path = save_path
        self.gt_list = gt_list

    def run(self):

        self.num_processed = 0

        # Save all gt data (masks, markups, etc)
        for gt in self.gt_list:
            gt.save_to_file(self.save_path)

            self.num_processed += 1

        print("gt save thread complete.")

        return

class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi(main_qt_ui, self)
        self.setMouseTracking(True)

        # Trial version flags
        self.tool_version = "1.0.3"
        #self.trial_version = True
        self.trial_version = False

        if self.trial_version == True:
            self.version_string = "Trial Version"
        else:
            self.version_string = "Licensed Version"

        self.logger = None

        self.label_version_info = self.findChild(QtWidgets.QLabel,"label_version_info")
        self.label_version_info.setText(self.version_string)

        if self.trial_version == True:
            self.label_version_info.setStyleSheet('color: red')
        else:
            self.label_version_info.setStyleSheet('color: green')

        # UI element initialization
        self.img_file_name = "Image File Unassigned"
        self.label_img_file_name = self.findChild(QtWidgets.QLineEdit,"img_file_name")
        self.label_img_file_name.setText(self.img_file_name)
        self.label_img_file_name.setReadOnly(True)
        self.base_img_file_name = self.img_file_name

        self.img_file_num = 0
        self.label_img_file_num = self.findChild(QtWidgets.QLabel,"img_file_num")
        self.label_img_file_num.setText(str(self.img_file_num))

        self.img_files_max = 0
        self.label_img_files_max = self.findChild(QtWidgets.QLabel,"img_files_max")
        self.label_img_files_max.setText("Total Image Files: " + str(self.img_files_max))

        self.img_file_path = "Image Folder Unassigned"

        self.gt_file_path = "GT Folder Unassigned"
        self.gt_list = []
        self.gt_progressbar = self.findChild(QtWidgets.QProgressBar,"gt_progressbar")
        self.gt_progressbar.setValue(0)

        self.label_file_path = "Label File Path Unassigned"
        self.label_list = []
        self.class_label = ObjectLabel()
        self.label_num = 0
        self.label_class_name = self.findChild(QtWidgets.QLabel,"label_class_name")
        color_str = "color: " + self.class_label.color
        self.label_class_name.setStyleSheet(color_str)
        self.label_class_name.setText(self.class_label.name)
        self.label_brush_size = 20
        self.min_brush_size = 5
        self.max_brush_size = 150

        self.cursor_x = 0
        self.cursor_y = 0
        self.label_cur_pos = self.findChild(QtWidgets.QLabel,"label_cur_pos")
        self.label_cursor_pos.setText("(" + str(self.cursor_x) + "," + str(self.cursor_y) + ")")

        self.num_markups = 0
        self.label_num_markups = self.findChild(QtWidgets.QLineEdit,"label_num_markups")
        self.label_num_markups.setText(str(self.num_markups))

        self.img_width = 0
        self.img_height = 0
        self.label_native_img_dims = self.findChild(QtWidgets.QLabel,"label_native_img_dims")
        self.label_native_img_dims.setText("Native Image Dims: (" + str(self.img_width) + "," + str(self.img_height) + ")")

        self.image_pane = self.findChild(QtWidgets.QLabel,"image_pane")
        self.image_pane.installEventFilter(self)
        self.image = None
        self.img_pixmap = None
        self.img_pane_width = 800
        self.img_pane_height = 600
        self.label_display_dims = self.findChild(QtWidgets.QLabel,"label_display_dims")
        self.label_display_dims.setText("Display Dims: (" + str(self.img_pane_width) + "," + str(self.img_pane_height) + ")")

        self.load_title()

        self.zoom_ctrl = ZoomControl(0,0,self.img_pane_width, self.img_pane_height)
        self.zoom_mode = False
        self.brush_resize_mode = False

        self.mask_opacity = 0.4
        self.show_mask = True
        self.mask_overlay = None
        self.label_mask_opacity = self.findChild(QtWidgets.QLabel,"label_mask_opacity_value")
        self.label_mask_opacity.setText("Mask Opacity: " + str(self.mask_opacity))
        self.slider_mask_opacity = self.findChild(QtWidgets.QSlider,"slider_mask_opacity")
        self.slider_mask_opacity.setValue(int(self.mask_opacity*100))
        self.slider_mask_opacity.valueChanged[int].connect(self.opacity_slider_changed)

        self.setup_button = self.findChild(QtWidgets.QPushButton,"setup_button")
        self.setup_button.clicked.connect(self.setup_mode)
        self.load_files_button = self.findChild(QtWidgets.QPushButton,"load_files_button")
        self.load_files_button.clicked.connect(self.use_settings)
        self.help_button = self.findChild(QtWidgets.QPushButton,"help_button")
        self.help_button.clicked.connect(self.help_mode)

        self.save_gt_file_button = self.findChild(QtWidgets.QPushButton,"gt_file_save")
        self.save_gt_file_button.clicked.connect(self.save_gt_data)

        self.normalize_gt_coords = False

        self.file_slider = self.findChild(QtWidgets.QSlider,"file_slider")
        self.file_slider.valueChanged[int].connect(self.file_slider_changed)

        self.label_privacy_policy_url = self.findChild(QLabel,"label_privacy_policy_url")
        self.label_privacy_policy_url.linkActivated.connect(self.privacy_link)
        self.label_privacy_policy_url.setText('<a href="http://trahmstechnologies.com/index.php/privacy-policy/">Trahms Technologies LLC Data Privacy Policy URL')

        self.help_dialog = HelpDialog()
        self.help_dialog.loadUi(help_qt_ui, help_image, app_icon)
        self.help_dialog.setFixedSize(self.help_dialog.size())  # prevent resizing
        self.help_dialog.hide()

        self.setup_dialog = SetupDialog()
        self.setup_dialog.loadUi(setup_qt_ui,app_icon)
        #self.setup_dialog.setFixedSize(self.setup_dialog.size())  # prevent resizing
        self.setup_dialog.hide()

        self.show()

    def load_title(self):
        # load image from file
        self.image = QImage(title_image)
        self.image = self.image.scaled(QSize(self.img_pane_width, self.img_pane_height))
        self.img_pixmap = QPixmap.fromImage(self.image)

        # blit pixmap to image pane
        self.image_pane.setPixmap(self.img_pixmap)

    def privacy_link(self, linkStr):
        QDesktopServices.openUrl(QUrl(linkStr))

    def refresh_labels(self):
        self.label_img_file_name.setText(self.base_img_file_name)
        self.label_img_file_num.setText(str(self.img_file_num))
        self.label_img_files_max.setText("Total Image Files: " + str(self.img_files_max))
        color_str = "color: " + self.class_label.color
        self.label_class_name.setStyleSheet(color_str)
        self.label_class_name.setText(self.class_label.name)
        self.label_mask_opacity.setText("Mask Opacity: " + str(self.mask_opacity))
        self.label_display_dims.setText("Display Dims: (" + str(self.img_pane_width) + "," + str(self.img_pane_height) + ")")

        if self.img_files_max > 0:
            img_w = self.gt_list[self.img_file_num].image_width
            img_h = self.gt_list[self.img_file_num].image_height
            self.label_native_img_dims.setText("Native Image Dims: (" + str(img_w) + "," + str(img_h) + ")")

        if len(self.gt_list) > 0:
            self.num_markups = self.gt_list[self.img_file_num].num_markups()
            self.label_num_markups.setText(str(self.num_markups))

        disp_x, disp_y = self.zoom_ctrl.getZoomLens(self.cursor_x, self.cursor_y)
        self.label_cursor_pos.setText("(" + str(disp_x) + "," + str(disp_y) + ")")

    def change_auto_key_state(self, b):
        self.auto_key_mode = not self.auto_key_mode

    def update_image(self):
        #print("update_image...")

        # grab new pixmap from current image
        self.img_pixmap = QPixmap.fromImage(self.image)
        self.img_pixmap = self.img_pixmap.scaled(QSize(self.img_pane_width,self.img_pane_height))

        # read in from file (or create a pixmap)
        #if self.mask_overlay == None:
        self.mask_overlay = QPixmap(self.img_pane_width, self.img_pane_height)
        self.mask_overlay.fill(Qt.GlobalColor.transparent)

        self.crosshair_overlay = QPixmap(self.img_pane_width, self.img_pane_height)
        self.crosshair_overlay.fill(Qt.GlobalColor.transparent)

        qp = QtGui.QPainter(self.mask_overlay)
        #qp.begin(self)  # redundant with QPainter creation

        # draw current GT from the gt list
        if len(self.gt_list) > 0:
            self.gt_list[self.img_file_num].draw_mask_and_markups(qp,self.show_mask)
            self.label_native_img_dims.setText("Native Image Dims: (" + str(self.gt_list[self.img_file_num].image_width) + "," + str(self.gt_list[self.img_file_num].image_height) + ")")

        qp.end()

        qp = QtGui.QPainter(self.crosshair_overlay)
        #qp.begin(self)  # redundant with QPainter creation

        # draw zoombox - debug only
        #self.zoom_ctrl.draw(qp)

        # draw crosshairs and brush target
        qp.setPen(QPen(QBrush(Qt.GlobalColor.yellow), 1, Qt.PenStyle.DashLine))
        qp.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        qp.drawLine(0, self.cursor_y, (self.img_pane_width-1),self.cursor_y)
        qp.drawLine(self.cursor_x,0,self.cursor_x,(self.img_pane_height-1))

        # draw color brush (with correct size)
        brush_x = int(self.cursor_x - self.label_brush_size/2)
        brush_y = int(self.cursor_y - self.label_brush_size/2)
        brush_size = int(self.label_brush_size)
        qp.drawEllipse(brush_x,brush_y,brush_size,brush_size)

        qp.end()

        # draw overlay on image
        result = QPixmap(self.img_pane_width, self.img_pane_height)
        qp = QtGui.QPainter(result)
        #qp.begin(self)      # redundant with QPainter creation
        qp.drawPixmap(0,0,self.img_pixmap)
        qp.setOpacity(self.mask_opacity)
        qp.drawPixmap(0,0,self.mask_overlay)
        qp.end()

        # zoom box
        rect = self.zoom_ctrl.getCropRect()
        result = result.copy(rect).scaled(QSize(self.img_pane_width,self.img_pane_height))

        # final step: overlay crosshairs & brush reticle
        result2 = QPixmap(self.img_pane_width, self.img_pane_height)
        qp = QtGui.QPainter(result2)
        #qp.begin(self)  # redundant with QPainter creation
        qp.drawPixmap(0,0,result)
        qp.setOpacity(1.0)
        qp.drawPixmap(0,0,self.crosshair_overlay)
        qp.end()

        # blit pixmap to image pane
        self.image_pane.setPixmap(result2)

        # update image info labels
        #self.img_width = self.image.width()
        #self.img_height = self.image.height()

        self.refresh_labels()

    def load_image_file_util(self, value):

        # bounds check
        if value < 0 or value > self.img_files_max - 1:
            return None

        # construct file path
        full_path_img_file_name = self.img_file_list[value]
        q_image = QImage(full_path_img_file_name)
        #q_image = q_image.convertToFormat(QImage.Format_Grayscale8)
        q_image = q_image.convertToFormat(QImage.Format.Format_RGB888)

        return q_image

    def load_image_file(self, value):
        self.img_file_num = value

        self.full_path_img_file_name = self.img_file_list[self.img_file_num]
        self.base_img_file_name = os.path.basename(self.full_path_img_file_name)
        self.image = self.load_image_file_util(value)

        # record actual native image dimensions before rescale
        img_width = self.image.width()
        img_height = self.image.height()

        # for display only, convert current image to proper image pane scale
        self.image = self.image.scaled(QSize(self.img_pane_width,self.img_pane_height))

        return img_width, img_height

    def load_image_file_list(self):
        self.logger.log("Reading JPG filenames from directory: " + self.img_file_path)

        self.img_file_list = sorted(glob.glob(self.img_file_path + "/*.jpg"))
        #print(self.img_file_list)

        self.img_files_max = len(self.img_file_list)
        self.img_file_num = 0
        self.logger.log("Number of JPG files identified: " + str(self.img_files_max))

        self.file_slider.setMinimum(0)
        self.file_slider.setMaximum(self.img_files_max-1)
        self.file_slider.setValue(0)

        self.num_gt_processed = 0
        self.gt_progressbar = self.findChild(QtWidgets.QProgressBar,"gt_progressbar")
        self.gt_progressbar.setValue(0)

        # start up gt load thread
        self.gt_loader = GT_Load_Process()
        self.gt_loader.load_params(self.img_file_list, self.gt_list)
        self.gt_loader.start()

        # start up status timer
        self.generateTimer = QTimer()
        self.generateTimer.timeout.connect(self.check_gt_load)
        self.generateTimer.start(100)

    def check_gt_load(self):
        self.num_gt_processed = self.gt_loader.check_progress()
        percent_done = int((self.num_gt_processed * 100)/len(self.img_file_list))
        self.gt_progressbar = self.findChild(QtWidgets.QProgressBar,"gt_progressbar")
        self.gt_progressbar.setValue(percent_done)

        num_gt_entries = len(self.img_file_list)
        if self.num_gt_processed < num_gt_entries:
            # reset status timer
            self.generateTimer = QTimer()
            self.generateTimer.timeout.connect(self.check_gt_load)
            self.generateTimer.start(100)
        else:
            self.generateTimer.stop()
            # all done
            if self.img_files_max > 0:
                # image_width, image_height = self.load_image_file(0)
                self.img_width, self.img_height = self.load_image_file(0)
                self.gt_list[0].set_img_dims(self.image, self.img_width, self.img_height)
                self.gt_list[0].set_disp_dims(self.img_pane_width, self.img_pane_height)
                self.overlay_mask = self.gt_list[0].load_from_file(self.gt_load_file_path)

            # force redraw
            self.update_image()

        return

    def load_label_list(self):
        # reset label_list
        self.label_list = []

        try:
            label_stream = open(self.label_file_path, "r")
        except (FileNotFoundError):
            return

        label = label_stream.readline()
        while label:
            newLabel = ObjectLabel()
            objcolorlist = label.strip().split(":")
            newLabel.name = objcolorlist[0].strip()
            newLabel.color = objcolorlist[1].strip()

            self.label_list.append(newLabel)
            label = label_stream.readline()
        label_stream.close()

        self.logger.log("Number of class labels identified: " + str(len(self.label_list)))
        self.logger.log("Labels:")
        for l in self.label_list:
            self.logger.log(l.name + "- color (RGB hex): " + l.color)

        print(self.label_list)

        if len(self.label_list) > 0:
            self.class_label = self.label_list[0]

        self.refresh_labels()

    def save_gt_data(self):
        # reload gt file path from the setup panel
        # (in case user has changed the name to something different than previously used)
        self.gt_save_file_path = self.setup_dialog.get_gt_save_file_path()

        if self.gt_save_file_path == "GT Save File Path Unassigned":
            return

        if len(self.gt_list) == 0:
            return

        # if directory doesn't exist, create it
        if os.path.isdir(self.gt_save_file_path) == False:
            if self.logger != None:
                self.logger.log("GT destination " + self.gt_save_file_path + " doesn't exist.  Creating!")
            os.mkdir(self.gt_save_file_path)

        print("save_gt_data() called.  Saving GT to " + self.gt_save_file_path)
        if self.logger != None:
            self.logger.log("Saving GT to " + self.gt_save_file_path)

        # Save all gt data (masks, markups, etc)
        #for gt in self.gt_list:
        #    gt.save_to_file(self.gt_save_file_path)

        self.num_gt_processed = 0
        self.gt_progressbar = self.findChild(QtWidgets.QProgressBar,"gt_progressbar")
        self.gt_progressbar.setValue(0)

        # start up gt save thread
        self.gt_saver = GT_Save_Process()
        self.gt_saver.load_params(self.gt_save_file_path,self.gt_list)
        self.gt_saver.start()

        # start up status timer
        self.generateTimer = QTimer()
        self.generateTimer.timeout.connect(self.check_gt_save)
        self.generateTimer.start(100)

    def check_gt_save(self):
        self.num_gt_processed = self.gt_saver.check_progress()
        percent_done = int((self.num_gt_processed * 100)/len(self.gt_list))
        self.gt_progressbar = self.findChild(QtWidgets.QProgressBar,"gt_progressbar")
        self.gt_progressbar.setValue(percent_done)

        if self.num_gt_processed < len(self.gt_list):
            # reset status timer
            self.generateTimer = QTimer()
            self.generateTimer.timeout.connect(self.check_gt_save)
            self.generateTimer.start(100)

        return


    def use_settings(self):

        # reset all variables
        self.image_file_list = []
        self.gt_list = []
        self.label_list = []
        self.img_file_num = 0
        self.img_files_max = 0
        self.file_slider.setValue(0)

        settings_yaml_file_path = self.setup_dialog.get_settings_yaml_file_path()
        if settings_yaml_file_path == "DL Segmenter Settings YAML Path Unassigned":
            return

        # load in paths from tool setup panel
        self.img_file_path = self.setup_dialog.get_img_file_path()
        self.label_file_path = self.setup_dialog.get_label_file_path()
        self.gt_load_file_path = self.setup_dialog.get_gt_load_file_path()
        self.gt_save_file_path = self.setup_dialog.get_gt_save_file_path()
        self.event_log_file_path = self.setup_dialog.get_event_log_file_path()

        self.logger = Logger(self.event_log_file_path)
        self.logger.log("DL Segmenter Event Log")
        self.logger.log("Version " + self.tool_version + " Trial = " + str(self.trial_version))

        self.logger.log("Loading setup file information...")

        # load 'em up!
        self.load_image_file_list()
        self.load_label_list()

    def help_mode(self):
        if self.logger != None:
            self.logger.log("Help mode, calling up dialog")

        self.help_dialog.show()
        self.help_dialog.raise_()

    def setup_mode(self):
        if self.logger != None:
            self.logger.log("Setup mode, calling up dialog")

        self.setup_dialog.show()
        self.setup_dialog.raise_()

    def file_slider_changed(self, value):
        if self.img_files_max == 0:
            return

        self.img_width, self.img_height = self.load_image_file(value)
        self.gt_list[value].set_img_dims(self.image, self.img_width, self.img_height)
        self.gt_list[value].set_disp_dims(self.img_pane_width, self.img_pane_height)

        # current GT is empty (no mask, markups, etc) for current image only, attempt to load from file
        if self.gt_list[value].mask_image == None:
            self.overlay_mask = self.gt_list[value].load_from_file(self.gt_load_file_path)

        #print("current image native dims = (" + str(self.gt_list[value].image_width) + "," + str(self.gt_list[value].image_height) + ")")

        self.refresh_labels()
        self.update_image()

    def opacity_slider_changed(self, value):

        if self.img_files_max == 0:
            return

        self.mask_opacity = value/100

        if self.logger != None:
            self.logger.log("Opacity changed to " + str(self.mask_opacity))

        self.refresh_labels()
        self.update_image()

    def draw_processing(self, event):
        if self.image != None:
            self.update_image()

    def paintEvent(self,event):
        #print("paintEvent x = " + str(self.cursor_x) + ", y = " + str(self.cursor_y))
        return

    def mouse_press_processing(self, event):
        self.cursor_x = int(event.position().x())
        self.cursor_y = int(event.position().y())
        disp_x, disp_y = self.zoom_ctrl.getZoomLens(self.cursor_x, self.cursor_y)
        brush_size = self.zoom_ctrl.adjustBrushSize(self.label_brush_size)

        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            #print("Left Mouse Button Press! x = " + str(event.x()) + ", y = " + str(event.y()))
            markup = Markup(self.img_width, self.img_height, self.img_pane_width, self.img_pane_height)
            markup.setDispPoint(disp_x,disp_y,brush_size, self.class_label)
            self.gt_list[self.img_file_num].add(markup)
        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            #print("Right Mouse Button Press! x =" + str(event.x()) + ", y = " + str(event.y()))
            self.gt_list[self.img_file_num].remove_selected_markups(disp_x,disp_y,brush_size)

        self.draw_processing(event)
        self.refresh_labels()
        return True

    def mouse_release_processing(self, event):
        self.cursor_x = int(event.position().x())
        self.cursor_y = int(event.position().y())
        #if event.button() == QtCore.Qt.LeftButton:
        #    print("Left Mouse Button Release! x = " + str(event.x()) + ", y = " + str(event.y()))
        #elif event.button() == QtCore.Qt.RightButton:
        #    #print("Right Mouse Button Press! x =" + str(event.x()) + ", y = " + str(event.y()))

        self.draw_processing(event)
        self.refresh_labels()
        return True

    def mouse_motion_processing(self, event):
        self.cursor_x = int(event.position().x())
        self.cursor_y = int(event.position().y())
        disp_x, disp_y = self.zoom_ctrl.getZoomLens(self.cursor_x,self.cursor_y)

        brush_size = self.zoom_ctrl.adjustBrushSize(self.label_brush_size)

        if event.buttons() == QtCore.Qt.MouseButton.LeftButton:
            #print("Left Mouse Button Motion! x = " + str(event.x()) + ", y = " + str(event.y()))
            markup = Markup(self.img_width,self.img_height,self.img_pane_width, self.img_pane_height)
            markup.setDispPoint(disp_x, disp_y, brush_size, self.class_label)
            self.gt_list[self.img_file_num].add(markup)
        elif event.buttons() == QtCore.Qt.MouseButton.RightButton:
            #print("Right Mouse Button Press! x =" + str(event.x()) + ", y = " + str(event.y()))
            self.gt_list[self.img_file_num].remove_selected_markups(disp_x,disp_y,brush_size)

        self.draw_processing(event)
        self.refresh_labels()
        return True

    def resize_processing(self, event):
        self.img_pane_width = int(event.size().width())
        self.img_pane_height = int(event.size().height())

        #print("resize event: Image pane : (" + str(self.img_pane_width) + "," + str(self.img_pane_height) + ") aspect_ratio = " + str(self.aspect_ratio))

        if self.logger != None:
            self.logger.log("Image pane resize: (" + str(self.img_pane_width) + "," + str(self.img_pane_height) + ")")

        if self.zoom_ctrl != None:
            self.zoom_ctrl.updateImgDims(self.img_pane_width, self.img_pane_height)

        for gt in self.gt_list:
            gt.set_disp_dims(self.img_pane_width, self.img_pane_height)

        if self.img_files_max > 0:
            self.draw_processing(event)

        self.refresh_labels()

        return True

    # event method used by the image pane
    def eventFilter(self, source, event):

        if event.type() == QtCore.QEvent.Type.Resize:
            self.resize_processing(event)

        if self.img_files_max == 0:
            return super(Ui, self).eventFilter(source, event)

        if event.type() == QtCore.QEvent.Type.MouseMove:
            self.mouse_motion_processing(event)
        elif event.type() == QtCore.QEvent.Type.Wheel:
            y = event.angleDelta().y()
            if y > 0:
                if self.zoom_mode == True:
                    self.change_zoom(0.75)
                elif self.brush_resize_mode == True:
                    self.change_brush_size(2)
                else:
                    self.decrement_label()
            else:
                if self.zoom_mode == True:
                    self.change_zoom(1.5)
                elif self.brush_resize_mode == True:
                    self.change_brush_size(-2)
                else:
                    self.increment_label()
        elif event.type() == QtCore.QEvent.Type.MouseButtonPress:
            self.mouse_press_processing(event)
        elif event.type() == QtCore.QEvent.Type.MouseButtonRelease:
            self.mouse_release_processing(event)

        return super(Ui, self).eventFilter(source, event)

    def decrement_image(self, event, prediction):
        currVal = self.file_slider.value()
        if (currVal > 0):
            nextVal = currVal - 1
            self.img_file_num = nextVal
            self.file_slider.setValue(nextVal)

            # look at prev and next images
            prev_q_image = self.load_image_file_util(currVal)
            next_q_image = self.load_image_file_util(nextVal)

            if prediction == True and self.trial_version == False:
                self.gt_list[nextVal].predict_annotation(self.gt_list[currVal], prev_q_image, next_q_image)

            self.draw_processing(event)

    def increment_image(self, event, prediction):
        currVal = self.file_slider.value()
        if (currVal < self.img_files_max - 1):
            nextVal = currVal + 1
            self.img_file_num = nextVal
            self.file_slider.setValue(nextVal)

            # look at prev and next images
            prev_q_image = self.load_image_file_util(currVal)
            next_q_image = self.load_image_file_util(nextVal)

            if prediction == True and self.trial_version == False:
                self.gt_list[nextVal].predict_annotation(self.gt_list[currVal], prev_q_image, next_q_image)

            self.draw_processing(event)

    def decrement_label(self):
        currVal = self.label_num
        if (currVal > 0):
            self.label_num = currVal - 1
            self.class_label = self.label_list[self.label_num]
            self.logger.log("Changed label to " + self.class_label.name + ", color = " + self.class_label.color)
            self.refresh_labels()

    def increment_label(self):
        currVal = self.label_num
        if (currVal < len(self.label_list) - 1):
            self.label_num = currVal + 1
            self.class_label = self.label_list[self.label_num]
            self.logger.log("Changed label to " + self.class_label.name + ", color = " + self.class_label.color)
            self.refresh_labels()

    def change_zoom(self, value):
        self.logger.log("Changed zoom: " + str(value))
        disp_x, disp_y = self.zoom_ctrl.getZoomLens(self.cursor_x,self.cursor_y)
        self.zoom_ctrl.setZoom(disp_x, disp_y, value)

        self.update_image()
        self.refresh_labels()

    def change_brush_size(self, value):
        if value < 0 and self.label_brush_size <= self.min_brush_size:
            return

        if value > 0 and self.label_brush_size >= self.max_brush_size:
            return

        self.label_brush_size += value
        self.logger.log("Changed brush size: " + str(self.label_brush_size))

        self.update_image()
        self.refresh_labels()
        return

    def keyPressEvent(self, event):
        if self.img_files_max == 0:
            return super(Ui, self).keyPressEvent(event)

        key = event.key()

        if key == Qt.Key.Key_Control:
            if self.trial_version == False:
                self.zoom_mode = True

        if key == Qt.Key.Key_Shift:
            self.brush_resize_mode = True

        # forward one image - no prediction
        if key == Qt.Key.Key_D:
            self.increment_image(event, False)

        # back one image - no prediction
        if key == Qt.Key.Key_A:
            self.decrement_image(event, False)

        # increment label
        if key == Qt.Key.Key_S:
            self.increment_label()

        # decrement label
        if key == Qt.Key.Key_W:
            self.decrement_label()

        # forward one image - with prediction
        if key == Qt.Key.Key_E:
            self.increment_image(event, True)

        # back one image - with prediction
        if key == Qt.Key.Key_Q:
            self.decrement_image(event, True)

        # delete all markups for current image
        if key == Qt.Key.Key_G:
            if self.img_files_max > 0:
                self.logger.log("Delete all markups for image " + self.img_file_list[self.img_file_num])
                self.gt_list[self.img_file_num].delete_all_markups()

                # make any future mask visible again
                self.show_mask = True

                self.draw_processing(event)

        # toggle markup-only or full mask display
        if key == Qt.Key.Key_R:
            self.show_mask = not self.show_mask
            self.logger.log("Toggle show mask to " + str(self.show_mask))

            self.refresh_labels()
            self.draw_processing(event)

        # delete mask for current image
        if key == Qt.Key.Key_F:
            if self.img_files_max > 0:

                # delete current mask
                self.logger.log("Delete mask for image " + self.img_file_list[self.img_file_num])
                self.gt_list[self.img_file_num].delete_mask()

                # make any future mask visible again
                self.show_mask = True

                self.draw_processing(event)

        # process current markups into mask (with watershed processing)
        if key == Qt.Key.Key_V:
            if self.img_files_max > 0:
                self.logger.log("Watershed processing of markups for image " + self.img_file_list[self.img_file_num])

                # scale input image pixmap to display size
                input_image = self.image.scaled(QSize(self.img_pane_width, self.img_pane_height))

                # create mask object
                self.overlay_mask = QPixmap(self.img_pane_width, self.img_pane_height)
                self.overlay_mask.fill(Qt.GlobalColor.transparent)

                qp = QtGui.QPainter(self.overlay_mask)
                #qp.begin(self)   # redundant with QPainter creation

                #self.gt_list[self.img_file_num].process_mask(qp, self.image, self.overlay_mask, True)
                self.gt_list[self.img_file_num].process_mask(qp, input_image, self.overlay_mask, True)
                qp.end()

                # make mask visible (if not already)
                self.show_mask = True

                self.draw_processing(event)

        # process current markups into mask (NO watershed processing)
        if key == Qt.Key.Key_B:
            if self.img_files_max > 0:
                self.logger.log("Manual processing of markups for image " + self.img_file_list[self.img_file_num])

                # create mask object
                self.overlay_mask = self.gt_list[self.img_file_num].get_overlay_mask()

                qp = QtGui.QPainter(self.overlay_mask)
                qp.begin(self)
                self.gt_list[self.img_file_num].process_mask(qp, self.image, self.overlay_mask, False)
                qp.end()

                # make mask visible (if not already)
                self.show_mask = True

                self.draw_processing(event)


        return super(Ui, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if self.img_files_max == 0:
            return super(Ui, self).keyReleaseEvent(event)

        key = event.key()

        if key == Qt.Key.Key_Control:
            self.zoom_mode = False

        if key == Qt.Key.Key_Shift:
            self.brush_resize_mode = False

        #self.draw_processing()

        return super(Ui, self).keyReleaseEvent(event)

if __name__ == '__main__':
    resource_base = 'resources/'
    main_qt_ui = resource_base + 'main_window.ui'
    help_qt_ui = resource_base + 'help_dialog.ui'
    setup_qt_ui = resource_base + 'setup_dialog.ui'
    title_image = resource_base + 'dlsegmenter_titlepage.png'
    help_image = resource_base + 'dlsegmenter_controls.png'
    app_icon = resource_base + 'TT_Icon.png'

    app = QApplication(sys.argv)
    window = Ui()
    window.show()
    sys.exit(app.exec())
