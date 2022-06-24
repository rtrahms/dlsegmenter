from PyQt6.QtCore import QDir, Qt, QSize, QRect, QPoint
from PyQt6.QtGui import QImage, QPainter, QPalette, QPixmap, QBrush, QPen, QColor

class Markup:
    def __init__(self, img_w, img_h, disp_w, disp_h):
        self.image_width = img_w
        self.image_height = img_h
        self.pane_width = disp_w
        self.pane_height = disp_h

        self.cx = 0
        self.cy = 0
        self.brush_size = 1.0
        self.alpha = 255
        self.class_label = None

        self.x_min = self.cx - self.brush_size/2
        self.x_max = self.cx + self.brush_size/2
        self.y_min = self.cy - self.brush_size/2
        self.y_max = self.cy + self.brush_size/2

    def setNativePoint(self, cx, cy, brush_sz, class_label):
        self.cx = cx
        self.cy = cy
        self.brush_size = brush_sz
        self.class_label = class_label

    def setDispPoint(self, disp_cx, disp_cy, disp_brush_sz, class_label):
        x_scale = float(self.image_width / self.pane_width)
        y_scale = float(self.image_height / self.pane_height)
        self.cx = int(disp_cx * x_scale)
        self.cy = int(disp_cy * y_scale)
        self.brush_size = disp_brush_sz * x_scale
        self.class_label = class_label

        self.x_min = self.cx - self.brush_size/2
        self.x_max = self.cx + self.brush_size/2
        self.y_min = self.cy - self.brush_size/2
        self.y_max = self.cy + self.brush_size/2

    # def getNativeDims(self):
    #     return self.cx, self.cy, self.brush_size

    def setDisplayDims(self, disp_w, disp_h):
        self.pane_width = disp_w
        self.pane_height = disp_h

    def draw(self, qpainter):
        #color = QColor(Qt.yellow)
        if self.class_label != None:
            color = QColor(self.class_label.color)
        else:
            color = QColor(Qt.GlobalColor.transparent)
        color.setAlpha(self.alpha)
        qpainter.setPen(QPen(color, 1, Qt.PenStyle.SolidLine))
        qpainter.setBrush(QBrush(color,Qt.BrushStyle.SolidPattern))

        # brush_x = self.cx - self.brush_size/2
        # brush_y = self.cy - self.brush_size/2
        # brush_size = self.brush_size
        #
        # qpainter.drawEllipse(brush_x,brush_y,brush_size,brush_size)

        scale_x = float(self.pane_width / self.image_width)
        scale_y = float(self.pane_height / self.image_height)
        disp_cx = scale_x * self.cx
        disp_cy = scale_y * self.cy
        disp_brush_size = scale_x * self.brush_size

        brush_x = int(disp_cx - disp_brush_size/2)
        brush_y = int(disp_cy - disp_brush_size/2)
        brush_size = int(disp_brush_size)

        qpainter.drawEllipse(brush_x,brush_y,brush_size,brush_size)

    def contains_point(self, x_min, x_max, y_min, y_max):

        if (x_min <= self.cx <= x_max) and (y_min <= self.cy <= y_max):
            return True

        #if (self.x_min <= x <= self.x_max) and (self.y_min <= y <= self.y_max):
        #    return True

        return False