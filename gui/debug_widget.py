from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, 
                             QTextEdit)
from PyQt6.QtCore import Qt

class DebugWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Debug Information")
        self.setGeometry(100, 100, 400, 300)
        
        layout = QVBoxLayout(self)
        
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        
        layout.addWidget(QLabel("Debug Log:"))
        layout.addWidget(self.log_text_edit)
        
    def update_log(self, stats: dict):
        log_text = ""
        for key, value in stats.items():
            if isinstance(value, float):
                log_text += f"{key}: {value:.2f}\n"
            else:
                log_text += f"{key}: {value}\n"
        
        self.log_text_edit.setPlainText(log_text)

    def clear_log(self):
        self.log_text_edit.clear()
