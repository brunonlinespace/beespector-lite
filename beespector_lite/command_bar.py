from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QSizePolicy, QToolButton, QWidget


class RaisedMenuToolbar(QWidget):
    """Classic fixed row of raised text menu buttons.

    Lite deliberately uses the same interaction pattern as its permanent
    View / Help controls: each button opens a normal QMenu immediately.
    There are no tabs, pages, wheel gestures, or ribbon-style command rows.
    """

    def __init__(self, menus, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row = QHBoxLayout(self)
        row.setContentsMargins(5, 4, 5, 4)
        row.setSpacing(6)
        row.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.buttons = []
        for text, menu in menus:
            button = QToolButton(self)
            button.setText(str(text))
            button.setMenu(menu)
            button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            button.setAutoRaise(False)
            button.setFixedHeight(38)
            button.setMinimumWidth(68)
            row.addWidget(button)
            self.buttons.append(button)
        row.addStretch(1)
