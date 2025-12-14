import cv2
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage
from app.analysis_core import TennisAnalyzerCore 

class AIWorker(QThread):
    # Signals
    analysis_stats_signal = pyqtSignal(dict) # Comprehensive stats signal
    finished_signal = pyqtSignal()

    def __init__(self, settings):
        super().__init__()
        self.running = True
        self.analyzer = TennisAnalyzerCore(settings)
        self.fps = settings.get('fps', 30)

    def run(self):
        # The thread's event loop will be managed by Qt.
        # We just need to keep the thread alive.
        while self.running:
            self.msleep(100) # Sleep to avoid busy-waiting
    
    def stop(self):
        self.running = False
        self.quit()
        self.wait()

    def process_frame(self, frame):
        if not self.running:
            return

        try:
            self.analyzer.settings['fps'] = self.fps 
            annotated_frame, ball_pos_ratio, stats = self.analyzer.analyze_frame(frame)
            
            # Emit comprehensive stats
            self.analysis_stats_signal.emit(stats)
            
        except Exception as e:
            print(f"Processing Error in Thread: {e}")
            import traceback
            traceback.print_exc()

    def __del__(self):
        self.stop()