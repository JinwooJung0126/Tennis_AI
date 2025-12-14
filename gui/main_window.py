from PyQt6.QtWidgets import (QMainWindow, QStackedWidget, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QSizePolicy, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal
from .setup_widget import SetupWidget
from .video_widget import VideoWidget
from .ai_thread import AIWorker # Import AIWorker
from .debug_widget import DebugWidget # Import DebugWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tennis AI Coach - Pro Edition")
        self.resize(1400, 850)
        
        self.ai_thread = None # Initialize AI thread
        self.debug_widget = DebugWidget() # Create debug widget
        
        # 메인 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 전체 레이아웃
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)

        # 1. Top Navigation Bar
        self.setup_top_bar()
        main_layout.addWidget(self.top_bar_widget)

        # 2. Content Area (Stacked Widget)
        self.stack = QStackedWidget()
        
        # 페이지 생성 (순서: ResultPage를 먼저 만들고, SetupWidget에 넘겨줌)
        self.result_page = self.create_result_page()
        self.setup_page = SetupWidget(self)
        self.setup_page.analyze_video_signal.connect(self.start_analysis) # Connect setup_page signal
        
        self.stack.addWidget(self.setup_page)   # Index 0: Configuration
        self.stack.addWidget(self.result_page)  # Index 1: Result
        
        main_layout.addWidget(self.stack)

    def setup_top_bar(self):
        """상단 탭 메뉴 바"""
        self.top_bar_widget = QWidget()
        self.top_bar_widget.setFixedHeight(60)
        self.top_bar_widget.setStyleSheet("background-color: #333; border-bottom: 2px solid #555;")
        
        layout = QHBoxLayout(self.top_bar_widget)
        
        lbl_logo = QLabel("🎾 TENNIS AI")
        lbl_logo.setStyleSheet("color: white; font-size: 20px; font-weight: bold; padding-left: 10px;")
        
        self.btn_tab_config = QPushButton("1. Configuration")
        self.btn_tab_result = QPushButton("2. Analysis Result")
        
        for btn in [self.btn_tab_config, self.btn_tab_result]:
            btn.setFixedSize(200, 40)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton { color: #aaa; font-size: 16px; border: none; font-weight: bold;}
                QPushButton:checked { color: white; background-color: #555; border-bottom: 3px solid #FF5722; }
                QPushButton:hover { color: white; }
            """)
            
        self.btn_tab_config.setChecked(True)
        
        self.btn_tab_config.clicked.connect(lambda: self.switch_tab(0))
        self.btn_tab_result.clicked.connect(lambda: self.switch_tab(1))

        self.chk_show_debug = QCheckBox("Show Debug")
        self.chk_show_debug.setStyleSheet("color: white;")
        self.chk_show_debug.toggled.connect(self.toggle_debug_widget)
        
        layout.addWidget(lbl_logo)
        layout.addStretch()
        layout.addWidget(self.btn_tab_config)
        layout.addWidget(self.btn_tab_result)
        layout.addWidget(self.chk_show_debug)
        layout.addStretch()

    def toggle_debug_widget(self, checked):
        if checked:
            self.debug_widget.show()
        else:
            self.debug_widget.hide()

    def create_result_page(self):
        """결과 화면 구성"""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        toolbar = QHBoxLayout()
        toolbar.addStretch()
        
        btn_discard = QPushButton("🗑 Discard")
        btn_discard.setStyleSheet("background-color: #666; color: white; padding: 8px 16px;")
        btn_discard.clicked.connect(lambda: self.switch_tab(0))
        
        btn_save = QPushButton("💾 Save Project")
        btn_save.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 16px; font-weight: bold;")
        
        toolbar.addWidget(btn_discard)
        toolbar.addWidget(btn_save)
        
        # ★ 결과 비디오 위젯 (AI 영상이 나올 곳)
        self.result_video = VideoWidget()
        self.result_video.display_text("Ready for Analysis...")
        
        layout.addLayout(toolbar)
        layout.addWidget(self.result_video)
        
        return page

    def start_analysis(self, video_path: str, settings: dict):
        """
        SetupWidget에서 분석 시작 신호를 받으면 호출됩니다.
        AI 스레드를 시작하고 VideoWidget에 연결합니다.
        """
        self.switch_to_result_tab()
        self.result_video.load_video(video_path) # Load video in VideoWidget
        
        # Get FPS from VideoWidget after loading video
        video_fps = self.result_video.fps
        settings['fps'] = video_fps # Add FPS to settings for analyzer

        if self.ai_thread and self.ai_thread.isRunning():
            self.ai_thread.stop()

        self.ai_thread = AIWorker(settings)
        self.ai_thread.analysis_stats_signal.connect(self.result_video.update_analysis_data)
        self.ai_thread.analysis_stats_signal.connect(self.debug_widget.update_log) # Connect to debug widget
        self.ai_thread.finished_signal.connect(self.ai_analysis_finished)
        
        # Connect VideoWidget's frame signal to AIWorker's processing slot
        self.result_video.frame_to_process_signal.connect(self.ai_thread.process_frame)
        
        self.ai_thread.start()
        self.result_video.play_video() # Start video playback
        
        self.result_video.display_text("Analyzing video...") # Update message

    def ai_analysis_finished(self):
        """AI 분석 스레드가 완료될 때 호출됩니다."""
        print("AI Analysis Finished.")
        self.ai_thread = None # Clear thread reference
        self.result_video.display_text("Analysis Complete.") # Update message

    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.btn_tab_config.setChecked(True)
            self.btn_tab_result.setChecked(False)
        else:
            self.btn_tab_config.setChecked(False)
            self.btn_tab_result.setChecked(True)

    def switch_to_result_tab(self):
        self.switch_tab(1)
