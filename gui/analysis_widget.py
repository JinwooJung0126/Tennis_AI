from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class AnalysisWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # 타이틀
        title = QLabel("Analysis Data")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        # 데이터 예시 (나중에 AI 연결)
        layout.addWidget(QLabel("Ball Speed: - km/h"))
        layout.addWidget(QLabel("Spin Type: -"))
        layout.addWidget(QLabel("In/Out: -"))
        
        # 빈 공간 밀어내기 (위쪽으로 정렬)
        layout.addStretch()
        
        self.setLayout(layout)
