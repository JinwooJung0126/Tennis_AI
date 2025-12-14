from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect, 
                             QFrame, QHBoxLayout)
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush

# ==========================================================
# [Core Component] 테니스 코트를 직접 그리는 위젯
# ==========================================================
class CourtMapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #333333; border-radius: 5px;") 
        
        self.colors = {
            "Good": QColor("#4CAF50"), "Bad": QColor("#FF9800"),
            "Out": QColor("#F44336"), "Ball": QColor("#FFFF00")
        }
        self.ball_pos = None 
        self.bounce_history = [] 

    def set_shot_color(self, shot_type, color):
        self.colors[shot_type] = color
        self.update()

    def update_ball_position(self, x_ratio, y_ratio):
        self.ball_pos = (x_ratio, y_ratio)
        self.update()

    def update_bounce_history(self, history: list):
        """AI Core에서 보낸 누적 바운스 히스토리 데이터를 받음"""
        self.bounce_history = history
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#2b2b2b"))

        pen = QPen(QColor("white"), 2)
        painter.setPen(pen)
        
        w = self.width(); h = self.height()
        mx = w * 0.15; my = h * 0.1
        cw = w - (2 * mx); ch = h - (2 * my)
        
        # 코트 라인 그리기 (비율 기반)
        painter.drawRect(int(mx), int(my), int(cw), int(ch)) # 외곽선
        
        singles_margin = cw * 0.15
        painter.drawLine(int(mx+singles_margin), int(my), int(mx+singles_margin), int(h-my))
        painter.drawLine(int(w-mx-singles_margin), int(my), int(w-mx-singles_margin), int(h-my))
        
        service_margin = ch * 0.25 
        painter.drawLine(int(mx+singles_margin), int(my+service_margin), int(w-mx-singles_margin), int(my+service_margin))
        painter.drawLine(int(mx+singles_margin), int(h-my-service_margin), int(w-mx-singles_margin), int(h-my-service_margin))
        painter.drawLine(int(w/2), int(my+service_margin), int(w/2), int(h-my-service_margin))
        painter.drawLine(int(mx-5), int(h/2), int(w-mx+5), int(h/2)) # 네트

        # 1. 누적 바운스 히스토리 점 그리기
        for bounce_x, bounce_y, result_type in self.bounce_history:
            color = self.colors.get(result_type, QColor("gray"))
            
            draw_x = bounce_x * w
            draw_y = bounce_y * h
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPoint(int(draw_x), int(draw_y)), 4, 4)

        # 2. 현재 공 그리기 (노란 점)
        if self.ball_pos:
            bx, by = self.ball_pos
            draw_x = bx * w
            draw_y = by * h
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(self.colors["Ball"]))
            painter.drawEllipse(QPoint(int(draw_x), int(draw_y)), 6, 6)

# ==========================================================
# [Interaction Component] 크기 조절/이동이 가능한 껍데기
# ==========================================================
class ResizableDraggableWidget(QWidget):
    """이동 및 크기 조절이 가능한 기본 위젯 클래스"""
    HANDLE_SIZE = 8; BORDER_WIDTH = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_selected = False; self.is_dragging = False; self.is_resizing = False
        self.resize_edge = None; self.drag_start_pos = QPoint()
        
        # 투명도 효과 (QGraphicsOpacityEffect 사용)
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0.8)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.setMouseTracking(True)
        self.setAutoFillBackground(True)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0);") # 배경 투명

    def set_opacity_value(self, percent):
        opacity = max(0.1, min(1.0, percent / 100.0))
        self.opacity_effect.setOpacity(opacity)

    def deselect(self):
        if self.is_selected:
            self.is_selected = False; self.update()

    def paintEvent(self, event):
        if self.is_selected:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            pen = QPen(QColor("#0078D7"), self.BORDER_WIDTH)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            rect = self.rect().adjusted(self.HANDLE_SIZE//2, self.HANDLE_SIZE//2, -self.HANDLE_SIZE//2, -self.HANDLE_SIZE//2)
            painter.drawRect(rect)
            
            painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor("white"))
            w, h = self.width(), self.height(); hs = self.HANDLE_SIZE
            points = [(0,0), (w//2-hs//2,0), (w-hs,0), (w-hs,h//2-hs//2), (w-hs,h-hs), (w//2-hs//2,h-hs), (0,h-hs), (0,h//2-hs//2)]
            for x, y in points: painter.drawRect(x, y, hs, hs)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_selected = True; self.update()
            edge = self.get_cursor_edge(event.pos())
            if edge:
                self.is_resizing = True; self.resize_edge = edge; self.drag_start_pos = event.globalPosition().toPoint()
            else:
                self.is_dragging = True; self.drag_start_pos = event.pos(); self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            self.is_selected = False; self.update()

    def mouseMoveEvent(self, event):
        if not self.is_dragging and not self.is_resizing:
            edge = self.get_cursor_edge(event.pos())
            if edge: self.update_cursor_shape(edge)
            else: self.setCursor(Qt.CursorShape.PointingHandCursor) 
        if self.is_dragging:
            self.move(self.mapToParent(event.pos()) - self.drag_start_pos)
        if self.is_resizing:
            global_pos = event.globalPosition().toPoint()
            diff = global_pos - self.drag_start_pos
            self.drag_start_pos = global_pos
            geo = self.geometry()
            left, top, w, h = geo.left(), geo.top(), geo.width(), geo.height()
            if 'L' in self.resize_edge: left += diff.x(); w -= diff.x()
            if 'R' in self.resize_edge: w += diff.x()
            if 'T' in self.resize_edge: top += diff.y(); h -= diff.y()
            if 'B' in self.resize_edge: h += diff.y()
            if w > 100 and h > 100: self.setGeometry(left, top, w, h)

    def mouseReleaseEvent(self, event):
        self.is_dragging = False; self.is_resizing = False; self.setCursor(Qt.CursorShape.ArrowCursor)

    def get_cursor_edge(self, pos):
        m = 10; w, h = self.width(), self.height(); x, y = pos.x(), pos.y(); edge = ""
        if y < m: edge += "T"
        elif y > h - m: edge += "B"
        if x < m: edge += "L"
        elif x > w - m: edge += "R"
        return edge if edge else None

    def update_cursor_shape(self, edge):
        if edge in ["T", "B"]: self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif edge in ["L", "R"]: self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edge in ["TL", "BR"]: self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edge in ["TR", "BL"]: self.setCursor(Qt.CursorShape.SizeBDiagCursor)

# ==========================================================
# [Composite Component] 최종 분석 대시보드
# ==========================================================
class AnalysisOverlay(ResizableDraggableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(220, 380)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10); layout.setSpacing(0)
        
        # 1. 코트 맵
        self.court_map = CourtMapWidget() 
        self.court_map.setMinimumHeight(200)
        
        # 2. 스탯 정보
        self.stats_area = QFrame()
        self.stats_area.setStyleSheet("background-color: rgba(0,0,0, 150); border-bottom-left-radius: 5px; border-bottom-right-radius: 5px;")
        stats_layout = QVBoxLayout(self.stats_area)
        stats_layout.setContentsMargins(10, 10, 10, 10)
        
        self.lbl_speed = QLabel("🚀 0 km/h"); self.lbl_spin = QLabel("🔄 Topspin"); self.lbl_type = QLabel("🎾 Forehand")
        for lbl in [self.lbl_speed, self.lbl_spin, self.lbl_type]:
            lbl.setStyleSheet("color: white; font-size: 13px; font-weight: bold; border: none; background: transparent;")
            stats_layout.addWidget(lbl)
            
        layout.addWidget(self.court_map, stretch=3)
        layout.addWidget(self.stats_area, stretch=1)
        self.setLayout(layout)

    def update_colors(self, shot_type, color):
        self.court_map.set_shot_color(shot_type, color)
        
    def update_ball_on_map(self, x, y):
        self.court_map.update_ball_position(x, y)