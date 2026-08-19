"""Reusable pitch visualization for tactic formations."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from fmsat.app.colourPalette import formationRows, formationUnknown
from fmsat.app.tacticDetailModel import DisplaySlot


class PitchWidget(QWidget):
    """Draw a scalable football pitch populated by formation slots."""

    def __init__(self, slots: tuple[DisplaySlot, ...], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.slots = slots
        self.setMinimumSize(520, 500)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pitch = QRectF(self.rect()).adjusted(18, 18, -18, -18)
        self._pitchDraw(painter, pitch)
        for slot in self.slots:
            self._slotDraw(painter, pitch, slot)

    @staticmethod
    def _pitchDraw(painter: QPainter, pitch: QRectF) -> None:
        painter.fillRect(painter.viewport(), QColor("#071c1c"))
        painter.fillRect(pitch, QColor("#123f35"))
        stripeHeight = pitch.height() / 10
        for index in range(0, 10, 2):
            stripe = QRectF(
                pitch.left(), pitch.top() + index * stripeHeight, pitch.width(), stripeHeight
            )
            painter.fillRect(stripe, QColor("#16493d"))
        painter.setPen(QPen(QColor("#82a99d"), 1.4))
        painter.drawRect(pitch)
        painter.drawLine(pitch.left(), pitch.center().y(), pitch.right(), pitch.center().y())
        painter.drawEllipse(pitch.center(), pitch.width() * 0.13, pitch.width() * 0.13)
        boxWidth = pitch.width() * 0.55
        boxHeight = pitch.height() * 0.16
        painter.drawRect(
            QRectF(pitch.center().x() - boxWidth / 2, pitch.top(), boxWidth, boxHeight)
        )
        painter.drawRect(
            QRectF(
                pitch.center().x() - boxWidth / 2,
                pitch.bottom() - boxHeight,
                boxWidth,
                boxHeight,
            )
        )

    @staticmethod
    def _slotDraw(painter: QPainter, pitch: QRectF, slot: DisplaySlot) -> None:
        centre = QPointF(
            pitch.left() + slot.x * pitch.width(),
            pitch.top() + slot.y * pitch.height(),
        )
        card = QRectF(centre.x() - 47, centre.y() - 24, 94, 48)
        colour = QColor(formationRows.get(slot.row, formationUnknown))
        painter.setPen(QPen(colour.lighter(145), 1.5))
        painter.setBrush(colour)
        painter.drawRoundedRect(card, 9, 9)
        painter.setPen(QColor("#ffffff"))
        roleFont = QFont(painter.font())
        roleFont.setBold(True)
        roleFont.setPointSize(10)
        painter.setFont(roleFont)
        painter.drawText(card.adjusted(4, 4, -4, -20), Qt.AlignmentFlag.AlignCenter, slot.role)
        detailFont = QFont(painter.font())
        detailFont.setBold(False)
        detailFont.setPointSize(7)
        painter.setFont(detailFont)
        painter.drawText(
            card.adjusted(3, 23, -3, -3),
            Qt.AlignmentFlag.AlignCenter,
            slot.position,
        )
