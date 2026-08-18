"""Non-modal source screenshot viewer."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget

from fmsat.app.ui.generated.ui_screenshotWindow import Ui_ScreenshotWindow


class ScreenshotWindow(QMainWindow):
    """Show one retained screenshot without blocking the management window."""

    def __init__(self, path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.path = path
        self.original = QPixmap(str(path))
        if self.original.isNull():
            raise ValueError(f"Unable to open screenshot: {path}")
        self.fitEnabled = True
        self.setWindowTitle(f"FMSAT source screenshot — {path.name}")

        self.ui = Ui_ScreenshotWindow()
        self.ui.setupUi(self)
        self.imageLabel = self.ui.image_label
        self.scrollArea = self.ui.scroll_area
        self.sizeButton = self.ui.size_button
        self.sizeButton.clicked.connect(self._sizeToggle)
        self.ui.close_button.clicked.connect(self.close)
        self._imageRefresh()

    @classmethod
    def pathOpen(cls, pathValue: str, parent: QWidget) -> ScreenshotWindow | None:
        """Validate and open a screenshot path, reporting legacy missing images."""

        path = Path(pathValue)
        if pathValue == "clipboard" or not path.is_file():
            QMessageBox.information(
                parent,
                "Screenshot unavailable",
                "This import does not have a retained source screenshot. "
                "Older clipboard imports cannot be recovered.",
            )
            return None
        try:
            viewer = cls(path, parent)
        except ValueError as exc:
            QMessageBox.warning(parent, "Screenshot unavailable", str(exc))
            return None
        viewer.windowPlaceBeside(parent)
        viewer.show()
        return viewer

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self.fitEnabled:
            self._imageRefresh()

    def windowPlaceBeside(self, reference: QWidget) -> None:
        """Place the viewer beside its source window where desktop space permits."""

        referenceScreen = reference.screen()
        otherScreens = [screen for screen in QApplication.screens() if screen != referenceScreen]
        if otherScreens:
            geometry = otherScreens[0].availableGeometry()
            self.resize(min(1000, geometry.width()), min(800, geometry.height()))
            self.move(geometry.topLeft())
            return
        available = referenceScreen.availableGeometry()
        referenceFrame = reference.frameGeometry()
        rightWidth = available.right() - referenceFrame.right()
        leftWidth = referenceFrame.left() - available.left()
        width = min(900, max(rightWidth, leftWidth))
        if width >= 400 and rightWidth >= leftWidth:
            self.resize(width, min(700, available.height()))
            self.move(referenceFrame.right() + 1, available.top())
        elif width >= 400:
            self.resize(width, min(700, available.height()))
            self.move(available.left(), available.top())
        else:
            self.resize(min(900, available.width()), min(700, available.height()))
            self.move(available.topRight() - self.rect().topRight())

    def _imageRefresh(self) -> None:
        if self.fitEnabled:
            size = self.scrollArea.viewport().size()
            pixmap = self.original.scaled(
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            pixmap = self.original
        self.imageLabel.setPixmap(pixmap)
        self.imageLabel.resize(pixmap.size())

    def _sizeToggle(self) -> None:
        self.fitEnabled = not self.fitEnabled
        self.scrollArea.setWidgetResizable(self.fitEnabled)
        self.sizeButton.setText("Actual size" if self.fitEnabled else "Fit window")
        self._imageRefresh()
