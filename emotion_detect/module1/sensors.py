# sensors.py
import serial
import time
import threading  # ? 스레드 추가
from datetime import datetime, timedelta

from config import (
    UART_DEVICES,
    BAUD,
    LUX_THRESHOLD,
    ECO2_THRESHOLD,
    TVOC_THRESHOLD,
    WATER_ALERT_INTERVAL_DAYS,
)
from emotion_detect.module1.notifier import play_tts, push_message
from emotion_detect.module1.camera_control import trigger_water_event, is_camera_enabled
from emotion_detect.module1.emotion import run as run_emotion

last_water_detected = None
alert_sent_for_no_water = False
sad_dates = set()

def check_continuous_sad():
    today = datetime.now().date()
    return all((today - timedelta(days=i)) in sad_dates for i in range(3))

def open_uart():
    for dev in UART_DEVICES:
        try:
            ser = serial.Serial(dev, BAUD, timeout=1)
            # ? 버퍼를 비워줌으로써 최신 데이터를 읽을 준비를 합니다.
            ser.flushInput() 
            print(f"[UART] Opened: {dev}")
            return ser
        except: continue
    raise RuntimeError("UART not available")

# ? 표정 인식과 알림을 담당할 별도의 작업 함수
def emotion_task(cam):
    global sad_dates
    print("[Thread] ? 표정 인식 스레드 시작")
    emo_result = run_emotion(cam)
    if emo_result == 'Sad':
        sad_dates.add(datetime.now().date())
        if check_continuous_sad():
            push_message("스마트 화분 알림", "?? 주인님이 3일 연속 슬퍼 보입니다. 기운 내세요!")
            sad_dates.clear()
    print("[Thread] ? 표정 인식 스레드 종료")

def handle_sensor_data_with_socket(cam, conn):
    global last_water_detected, alert_sent_for_no_water
    ser = open_uart()

    while True:
        # ? UART 버퍼가 너무 쌓이지 않도록 체크 (선택 사항)
        if ser.in_waiting > 500:
            ser.flushInput()

        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if not line:
            continue
        
        # 센서 데이터 출력 (실시간 확인용)
        print(f"[Sensor] RX: {line}")

        if "물 감지됨" in line or "물이 감지되었습니다" in line:
            if is_camera_enabled():
                last_water_detected = datetime.now()
                alert_sent_for_no_water = False
                
                # 1. 즉시 카메라 촬영 및 기본 알림 (비교적 빠름)
                trigger_water_event(cam)

                # 2. 소켓 전송 (비동기 처리가 필요할 수 있지만 우선 유지)
                try:
                    conn.sendall("run".encode())
                except: pass

                # 3. ? 표정 인식을 '스레드'로 분리하여 실행
                # 이제 센서 루프는 이 함수가 끝날 때까지 기다리지 않고 바로 다음 루프로 넘어갑니다.
                task = threading.Thread(target=emotion_task, args=(cam,), daemon=True)
                task.start()

        # --- 아래 센서 처리 로직이 이제 표정 인식 중에도 즉시 실행됩니다 ---
        if "조도:" in line:
            try:
                lux = float(line.split("조도:")[1].split(" lx")[0].strip())
                if lux >= LUX_THRESHOLD:
                    play_tts("오늘 날씨가 좋아요. 산책을 나가보세요.")
                    push_message("스마트 화분 알림", "?? 햇빛이 충분합니다.")
            except: pass
            
        # (eCO2, TVOC 처리 로직 생략 - 기존과 동일하게 유지)
        
        # CPU 점유율을 낮추기 위한 미세한 대기
        time.sleep(0.01)
