"""Non-modal source screenshot viewer."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


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
        self.resize(900, 650)

        content = QWidget(self)
        layout = QVBoxLayout(content)
        self.imageLabel = QLabel()
        self.imageLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidget(self.imageLabel)
        self.scrollArea.setWidgetResizable(True)
        layout.addWidget(self.scrollArea)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.sizeButton = QPushButton("Actual size")
        self.sizeButton.clicked.connect(self._sizeToggle)
        buttons.addWidget(self.sizeButton)
        closeButton = QPushButton("Close")
        closeButton.clicked.connect(self.close)
        buttons.addWidget(closeButton)
        layout.addLayout(buttons)
        self.setCentralWidget(content)
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

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
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
