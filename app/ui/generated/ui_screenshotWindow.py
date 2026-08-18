# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'screenshotWindow.ui'
##
## Created by: Qt User Interface Compiler version 6.11.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QDate,
    QDateTime,
    QLocale,
    QMetaObject,
    QObject,
    QPoint,
    QRect,
    QSize,
    QTime,
    QUrl,
    Qt,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontDatabase,
    QGradient,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPalette,
    QPixmap,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


class Ui_ScreenshotWindow(object):
    def setupUi(self, ScreenshotWindow):
        if not ScreenshotWindow.objectName():
            ScreenshotWindow.setObjectName("ScreenshotWindow")
        ScreenshotWindow.resize(900, 650)
        self.centralwidget = QWidget(ScreenshotWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.vrt_main = QVBoxLayout(self.centralwidget)
        self.vrt_main.setObjectName("vrt_main")
        self.scroll_area = QScrollArea(self.centralwidget)
        self.scroll_area.setObjectName("scroll_area")
        self.scroll_area.setWidgetResizable(True)
        self.image_label = QLabel()
        self.image_label.setObjectName("image_label")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.image_label)

        self.vrt_main.addWidget(self.scroll_area)

        self.hrz_buttons = QHBoxLayout()
        self.hrz_buttons.setObjectName("hrz_buttons")
        self.hrz_spacer = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        self.hrz_buttons.addItem(self.hrz_spacer)

        self.size_button = QPushButton(self.centralwidget)
        self.size_button.setObjectName("size_button")

        self.hrz_buttons.addWidget(self.size_button)

        self.close_button = QPushButton(self.centralwidget)
        self.close_button.setObjectName("close_button")

        self.hrz_buttons.addWidget(self.close_button)

        self.vrt_main.addLayout(self.hrz_buttons)

        ScreenshotWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(ScreenshotWindow)

        QMetaObject.connectSlotsByName(ScreenshotWindow)

    # setupUi

    def retranslateUi(self, ScreenshotWindow):
        ScreenshotWindow.setWindowTitle(
            QCoreApplication.translate("ScreenshotWindow", "FMSAT source screenshot", None)
        )
        self.image_label.setText("")
        self.size_button.setText(
            QCoreApplication.translate("ScreenshotWindow", "Actual size", None)
        )
        self.close_button.setText(QCoreApplication.translate("ScreenshotWindow", "Close", None))

    # retranslateUi
