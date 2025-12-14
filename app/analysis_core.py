import torch
from ultralytics import YOLO
import numpy as np
import cv2
from collections import deque
from typing import List, Tuple, Dict, Any
from itertools import combinations

class TennisAnalyzerCore:
    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.model = None
        self.device = 'cpu'
        
        # 30프레임 동안의 공 위치를 저장하는 버퍼 (deque 사용)
        self.trajectory_buffer = deque(maxlen=30) 
        # 최종 바운스 지점 히스토리 (SwingVision처럼 누적됨)
        # 형식: List[Tuple[float, float, str]] -> (x_ratio, y_ratio, result_color)
        self.bounce_history: List[Tuple[float, float, str]] = [] 
        
        # 1. GPU/CPU 디바이스 초기화 및 모델 로드
        try:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.model = YOLO('yolov8m.pt')
            self.model.to(self.device)
        except Exception as e:
            print(f"CORE ERROR: GPU initialization failed ({e}). Forcing CPU.")
            self.device = 'cpu'
            self.model = YOLO('yolov8m.pt')  # Consistent with the chosen model
            self.model.to(self.device)

        self.court_type = settings.get('court_type', 'Singles')
        self.H_matrix = None # Perspective transformation matrix
        self.court_lines_detected = False # Flag to indicate if court lines have been detected and H_matrix is set
        
    def _detect_court_lines(self, frame):
        """
        Detects court lines automatically using a more robust method.
        """
        # Preprocessing
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150, apertureSize=3)

        # Line detection
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 150)
        
        if lines is None:
            return None

        # Separate lines into horizontal and vertical
        h_lines, v_lines = [], []
        for line in lines:
            rho, theta = line[0]
            angle = np.degrees(theta)
            if (angle > 80 and angle < 100):
                v_lines.append([rho, theta])
            elif (angle < 10 or angle > 170):
                h_lines.append([rho, theta])

        if not h_lines or not v_lines:
            return None

        # Find the most prominent horizontal and vertical lines
        top_line = max(h_lines, key=lambda x: x[0])
        bottom_line = min(h_lines, key=lambda x: x[0])
        left_line = min(v_lines, key=lambda x: x[0])
        right_line = max(v_lines, key=lambda x: x[0])

        # Find intersections of these 4 lines
        lines = [top_line, bottom_line, left_line, right_line]
        intersections = []
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                rho1, theta1 = lines[i]
                rho2, theta2 = lines[j]
                A = np.array([[np.cos(theta1), np.sin(theta1)], [np.cos(theta2), np.sin(theta2)]])
                b = np.array([[rho1], [rho2]])
                try:
                    intersection = np.linalg.solve(A, b)
                    intersections.append(intersection.flatten())
                except np.linalg.LinAlgError:
                    continue

        if len(intersections) < 4:
            return None
        
        # Find the convex hull of the intersections to get the outer corners
        hull = cv2.convexHull(np.array(intersections, dtype=np.float32))
        
        if len(hull) < 4:
            return None
            
        # Approximate the hull to get 4 corners
        epsilon = 0.1 * cv2.arcLength(hull, True)
        approx = cv2.approxPolyDP(hull, epsilon, True)

        if len(approx) == 4:
            # Sort corners: top-left, top-right, bottom-right, bottom-left
            corners = sorted(approx.reshape(4, 2), key=lambda x: x[1])
            top_corners = sorted(corners[:2], key=lambda x: x[0])
            bottom_corners = sorted(corners[2:], key=lambda x: x[0], reverse=True)
            return [top_corners[0], top_corners[1], bottom_corners[0], bottom_corners[1]]
            
        return None

    def _calculate_perspective_transform(self, frame, court_corners_image_coords) -> np.ndarray:
        court_width = 1000
        court_height = 2000
        
        destination_pts = np.float32([
            [0, 0],
            [court_width - 1, 0],
            [court_width - 1, court_height - 1],
            [0, court_height - 1]
        ])

        source_pts = np.float32(court_corners_image_coords)
        
        if len(source_pts) != 4:
            return None

        H_matrix = cv2.getPerspectiveTransform(source_pts, destination_pts)
        return H_matrix

    def _transform_point_to_court(self, point_ratio: Tuple[float, float], frame_width: int, frame_height: int) -> Tuple[float, float] | None:
        if self.H_matrix is None:
            return None

        x_pixel = point_ratio[0] * frame_width
        y_pixel = point_ratio[1] * frame_height

        point_3d = np.array([[[x_pixel, y_pixel]]], dtype=np.float32)
        transformed_point = cv2.perspectiveTransform(point_3d, self.H_matrix)

        court_x = transformed_point[0][0][0] / 1000
        court_y = transformed_point[0][0][1] / 2000
        
        return (court_x, court_y)
        
    def _calculate_ball_speed(self, current_pos_court: Tuple[float, float], prev_pos_court: Tuple[float, float], fps: float) -> float:
        distance = np.sqrt((current_pos_court[0] - prev_pos_court[0])**2 + 
                           (current_pos_court[1] - prev_pos_court[1])**2)
        time_diff = 1.0 / fps
        speed = distance / time_diff
        return speed

    def _analyze_ball_trajectory(self) -> str:
        if len(self.trajectory_buffer) < 5:
            return "N/A"
        return "Flat"

    def analyze_frame(self, frame, conf=0.25):
        if self.model is None:
            return frame, None, {}

        # 0. Detect court lines and calculate perspective transform if not already done
        if not self.court_lines_detected:
            corners = self._detect_court_lines(frame)
            if corners and len(corners) == 4:
                self.H_matrix = self._calculate_perspective_transform(frame, corners)
                if self.H_matrix is not None:
                    self.court_lines_detected = True
                    print("Court automatically detected.")
                    # Draw corners for debugging
                    for x, y in corners:
                        cv2.circle(frame, (int(x), int(y)), 10, (0,0,255), -1)
                else:
                    print("Failed to calculate H_matrix from auto-detected corners.")
            else:
                print("Automatic court detection failed for this frame.")

        # 1. AI 추론 및 추적 (스포츠 공만 대상으로 지정)
        results = self.model.track(
            frame, 
            conf=conf, 
            verbose=False,
            persist=True, 
            tracker='bytetrack.yaml',
            classes=[32]  # 32번 클래스('sports ball')만 추적
        )
        
        annotated_frame = frame.copy()
        
        # 2. 공 좌표 찾기 및 계산
        frame_height, frame_width = frame.shape[:2]
        ball_pos_ratio = None
        ball_pos_court = None # New variable for court-transformed ball position
        
        if results[0].boxes.data.numel() > 0:
            # 공이 하나만 있다고 가정하고 첫 번째 공을 사용
            box_data = results[0].boxes.data[0]
            x1, y1, x2, y2 = box_data[0:4].tolist()
            
            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)
            
            # 프레임에 원 그리기
            cv2.circle(annotated_frame, (center_x, center_y), 5, (0, 255, 0), -1)

            ratio_x = center_x / frame_width
            ratio_y = center_y / frame_height
            ball_pos_ratio = (ratio_x, ratio_y)

            # Transform ball position to court coordinates
            ball_pos_court = self._transform_point_to_court(ball_pos_ratio, frame_width, frame_height)
            if ball_pos_court:
                # For debugging: print transformed court coordinates
                # print(f"Ball court position: {ball_pos_court[0]:.2f}, {ball_pos_court[1]:.2f}")
                pass
        
        # 3. 공 위치를 핵심 로직으로 전달하여 처리 (궤적 버퍼 업데이트 및 바운스 감지)
        # Pass both image ratio and court-transformed position
        # Need FPS for speed calculation, so passing it along
        fps = self.settings.get('fps', 30) # Get FPS from settings, default to 30
        self._process_ball_position(ball_pos_ratio, ball_pos_court, fps)

        # Retrieve analysis results to return
        ball_speed = self.latest_ball_speed if hasattr(self, 'latest_ball_speed') else 0.0
        ball_trajectory_type = self.latest_ball_trajectory_type if hasattr(self, 'latest_ball_trajectory_type') else "N/A"

        # 4. 반환값: 현재 프레임, 현재 공 위치 (이미지 비율), 누적 히스토리 데이터, 추가 통계
        return annotated_frame, ball_pos_ratio, {
            "bounce_history": self.bounce_history, 
            "ball_pos_court": ball_pos_court,
            "ball_speed": ball_speed,
            "ball_trajectory_type": ball_trajectory_type
        }

    def _process_ball_position(self, pos_image_ratio: Tuple[float, float] | None, pos_court: Tuple[float, float] | None, fps: float):
        """
        공 위치를 버퍼에 저장하고 바운스 여부를 판단합니다.
        `pos_image_ratio`: Ball position in image ratio (x, y)
        `pos_court`: Ball position in normalized court coordinates (x, y)
        `fps`: Frames per second of the video
        """
        # For bounce detection
        BOUNCE_THRESHOLD_Y = 0.01 # A small threshold for vertical movement to register a change
        # Initialize these if they don't exist
        if not hasattr(self, 'prev_ball_y_court'):
            self.prev_ball_y_court = None
            self.is_falling = False

        if pos_court is not None:
            # Store court-transformed position for speed calculation
            if len(self.trajectory_buffer) > 0 and self.trajectory_buffer[-1] is not None:
                # Only calculate speed if there's a previous valid court position
                prev_pos_court = self.trajectory_buffer[-1][1] # Get previous court position
                if prev_pos_court is not None:
                    self.latest_ball_speed = self._calculate_ball_speed(pos_court, prev_pos_court, fps)
                else:
                    self.latest_ball_speed = 0.0
            else:
                self.latest_ball_speed = 0.0
            
            # Bounce Detection Logic
            if self.prev_ball_y_court is not None:
                current_y = pos_court[1]
                # Check for a significant change in vertical direction
                if current_y > self.prev_ball_y_court + BOUNCE_THRESHOLD_Y: # Ball is moving down
                    self.is_falling = True
                elif current_y < self.prev_ball_y_court - BOUNCE_THRESHOLD_Y and self.is_falling: # Ball was falling and is now moving up
                    # Potential bounce detected!
                    # The bounce point is likely near the previous frame's ball position
                    if len(self.trajectory_buffer) > 0 and self.trajectory_buffer[-1][0] is not None:
                        bounce_pos_image_ratio = self.trajectory_buffer[-1][0]
                        # For now, classify as 'Good'. This would later be refined with court line detection
                        self.bounce_history.append((bounce_pos_image_ratio[0], bounce_pos_image_ratio[1], 'Good'))
                        print(f"Bounce detected at image ratio: {bounce_pos_image_ratio}")
                    self.is_falling = False # Reset falling state after bounce
            
            self.prev_ball_y_court = pos_court[1] # Update previous y position

            # Append (image_ratio, court_position) to buffer
            self.trajectory_buffer.append((pos_image_ratio, pos_court))
            
            # Analyze trajectory
            self.latest_ball_trajectory_type = self._analyze_ball_trajectory()

        else:
            # If ball is not detected, clear trajectory buffer (or implement occlusion prediction)
            self.trajectory_buffer.append((None, None)) # Append None for undetected frame
            self.latest_ball_speed = 0.0
            self.latest_ball_trajectory_type = "N/A"
            self.is_falling = False # Reset falling state if ball is lost
            
        return None
