# camera_control.py
import os, time, cv2
from gpiozero import LED, Button
from picamera2 import Picamera2
from config import LED_PIN, SWITCH_PIN, SAVE_PATH, LED_HOLD_SEC
from emotion_detect.module1.notifier import play_tts, push_message

led = LED(LED_PIN)
switch = Button(SWITCH_PIN, pull_up=True)

def open_camera():
    """카메라 초기화"""
    info = Picamera2.global_camera_info()
    print("[Pi] Cameras detected:", info)
    if not info:
        raise RuntimeError("No cameras detected.")
    cam = Picamera2()
    cam.configure(cam.create_still_configuration())
    cam.start()
    time.sleep(0.3)
    return cam

def show_image_if_gui(path: str, hold_ms: int = 2000):
    """DISPLAY가 있을 때만 이미지 표시"""
    if not os.environ.get("DISPLAY"):
        print(f"[Pi] (headless) Saved only: {path}")
        return
    img = cv2.imread(path)
    if img is None:
        print("[Pi] Failed to load image.")
        return
    cv2.imshow("Smart Flowerpot Capture", img)
    cv2.waitKey(hold_ms)
    cv2.destroyAllWindows()

def trigger_water_event(cam):
    """물 감지 시 실행되는 카메라 + LED + 알림 루틴"""
    print("[Camera] ? 물 감지 → 카메라 촬영 시작")
    led.on()
    cam.capture_file(SAVE_PATH)
    print(f"[Camera] Saved: {SAVE_PATH}")

    push_message("스마트 화분 알림", "? 물이 감지되었습니다!")
    play_tts("물이 감지되었습니다. 식물에게 물이 공급되었습니다.")

    time.sleep(LED_HOLD_SEC)
    # led.off()
    show_image_if_gui(SAVE_PATH)

def is_camera_enabled():
    """Privacy 스위치 상태 반환"""
    return switch.is_pressed  # True면 ON
