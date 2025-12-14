from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QStyle, QSlider, QSizePolicy)
from PyQt6.QtCore import Qt

class VolumeControlWidget(QWidget):
    def __init__(self, audio_output, parent=None):
        super().__init__(parent)
        self.audio_output = audio_output
        self.setMouseTracking(True)
        self.init_ui()
        
    def init_ui(self):
        self.layout = QVBoxLayout(self) # Use QVBoxLayout
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.btn_mute = QPushButton()
        self.btn_mute.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
        self.btn_mute.setCheckable(True) # Make it checkable for mute state
        self.btn_mute.clicked.connect(self._toggle_mute)
        
        self.volume_slider = QSlider(Qt.Orientation.Vertical)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.audio_output.volume() * 100))
        self.volume_slider.valueChanged.connect(self._set_volume)
        self.volume_slider.setVisible(False) # Initially hidden
        self.volume_slider.setFixedHeight(80) # Set a fixed height for the slider
        
        self.layout.addWidget(self.volume_slider, 0, Qt.AlignmentFlag.AlignHCenter) # Center the slider
        self.layout.addWidget(self.btn_mute)
        
        self.setLayout(self.layout)
        self.setFixedWidth(self.btn_mute.sizeHint().width()) # Adjust width
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

    def _toggle_mute(self):
        is_muted = self.btn_mute.isChecked()
        self.audio_output.setMuted(is_muted)
        if is_muted:
            self.btn_mute.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolumeMuted))
        else:
            self.btn_mute.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))

    def _set_volume(self, volume):
        self.audio_output.setVolume(volume / 100.0)
        if volume == 0:
            self.btn_mute.setChecked(True)
            self.btn_mute.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolumeMuted))
        elif self.btn_mute.isChecked():
            self.btn_mute.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
            self.btn_mute.setChecked(False)

    def enterEvent(self, event):
        super().enterEvent(event)
        self.volume_slider.setVisible(True)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if not self.rect().contains(event.position().toPoint()):
             self.volume_slider.setVisible(False)