# config.py
# 스마트 화분 공통 설정 파일 ?

# UART
UART_DEVICES = ("/dev/ttyAMA1", "/dev/serial0")
BAUD = 115200

# GPIO 핀 번호
LED_PIN = 18        # GPIO18 (핀12)
SWITCH_PIN = 23     # GPIO23 (핀16, GND 연결)

# 카메라 이미지 저장 경로
SAVE_PATH = "/home/pi/water_capture.jpg"

# 임계값 설정
LUX_THRESHOLD = 400      # lx
ECO2_THRESHOLD = 300     # ppm
TVOC_THRESHOLD = 200      # ppb
DEBOUNCE_SEC = 2.0        # 연속 트리거 방지
LED_HOLD_SEC = 3.0        # LED 점등 유지시간
WATER_ALERT_INTERVAL_DAYS = 3  # 물 미감지 알림 주기 (일)

# Pushbullet API Key
PUSHBULLET_KEY = "o.mcroMeE48bIbc0cADzbwJ0gbYlq7hlfo"

# Gemini API
GEMINI_API_KEY = "AIzaSyCPSIRQ56IYyHcI_etGGhU1_i2m4o-R2AU"