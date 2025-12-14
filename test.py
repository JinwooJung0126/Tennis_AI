# pre_download.py
from ultralytics import YOLO

print("YOLOv8s 모델 파일 다운로드 및 캐싱을 시작합니다. (약 20MB)")
print("다운로드 중 잠시 멈춰 보일 수 있으니 완료 메시지가 뜰 때까지 기다려 주세요.")

try:
    # 이 한 줄이 모델을 다운로드하고 시스템 캐시 폴더에 저장합니다.
    YOLO('yolov8s.pt')
    print("✅ 다운로드 및 캐싱 완료! 이제 Tennis_AI.py를 실행해도 멈추지 않습니다.")
except Exception as e:
    print(f"❌ 다운로드 실패! 인터넷 연결 상태를 확인하거나 재시도 해주세요. 오류: {e}")
