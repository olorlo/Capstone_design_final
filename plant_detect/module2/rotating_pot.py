# rotating_pot.py
from gpiozero import OutputDevice
import time
from smbus2 import SMBus
import threading

# -----------------------------
# 설정값
# -----------------------------
MEASURE_INTERVAL = 10
THRESH_ACC = 10
HALFSTEP_DELAY = 0.002

BH1750_ADDR = 0x23
BH1750_CMD = 0x10

PIN1 = 4
PIN2 = 17
PIN3 = 27
PIN4 = 22

motor_pins = [
    OutputDevice(PIN1),
    OutputDevice(PIN2),
    OutputDevice(PIN3),
    OutputDevice(PIN4)
]

halfstep_seq = [
    [1,0,0,0],
    [1,1,0,0],
    [0,1,0,0],
    [0,1,1,0],
    [0,0,1,0],
    [0,0,1,1],
    [0,0,0,1],
    [1,0,0,1]
]

current_step = 0  # 홈 위치 기준 누적 스텝

# -----------------------------
# BH1750 읽기
# -----------------------------
def read_light():
    with SMBus(1) as bus:
        bus.write_byte(BH1750_ADDR, BH1750_CMD)
        time.sleep(0.2)
        data = bus.read_i2c_block_data(BH1750_ADDR, 0x10, 2)
        lux = (data[0] << 8 | data[1]) / 1.2
        return lux

def _all_pins_off():
    for pin in motor_pins:
        pin.off()

# -----------------------------
# (중요) 스텝 실행: stop_event 체크하며 돌기
# -----------------------------
def _step_motor(seq, stop_event: threading.Event | None = None):
    """
    seq: halfstep_seq 또는 reversed seq
    stop_event가 set되면 즉시 중단하고 False 리턴
    """
    for step in seq:
        if stop_event is not None and stop_event.is_set():
            _all_pins_off()
            return False
        for pin, val in zip(motor_pins, step):
            pin.on() if val else pin.off()
        time.sleep(HALFSTEP_DELAY)
    return True

# -----------------------------
# 180도 회전 (중단 가능)
# -----------------------------
def rotate_180(direction=1, stop_event: threading.Event | None = None):
    global current_step
    seq = halfstep_seq if direction == 1 else list(reversed(halfstep_seq))

    # ? 256 "세트"라고 생각하고 있었는데,
    # 기존 구현은 256 * (8 halfstep) 만큼이라 꽤 많이 돎.
    # 기존 동작을 유지하되, 중간중간 stop_event로 끊을 수 있게만 개선.
    for _ in range(256):
        ok = _step_motor(seq, stop_event)
        if not ok:
            print("[회전 중단] rotate_180 stop_event 감지")
            return False

    current_step += 256 * direction
    _all_pins_off()
    return True

# -----------------------------
# 홈 위치 복귀 (중단 가능)
# -----------------------------
def return_home(stop_event: threading.Event | None = None):
    global current_step
    steps_needed = -current_step
    if steps_needed == 0:
        print("이미 홈 위치에 있습니다.")
        return True

    direction = 1 if steps_needed > 0 else -1
    seq = halfstep_seq if direction == 1 else list(reversed(halfstep_seq))

    for _ in range(abs(steps_needed)):
        ok = _step_motor(seq, stop_event)
        if not ok:
            print("[홈복귀 중단] stop_event 감지")
            return False

    current_step = 0
    _all_pins_off()
    print("홈 복귀 완료!")
    return True

# -----------------------------
# 자동 회전 루프 (stop_event 지원)
# -----------------------------
def rotate_loop(stop_event: threading.Event | None = None):
    """
    stop_event가 set되면:
      - 루프 종료
      - 안전하게 홈복귀 시도
    """
    accumulated_light = 0
    last_time = time.time()
    direction = 1

    try:
        while True:
            if stop_event is not None and stop_event.is_set():
                print("[rotate_loop 종료] stop_event 감지")
                break

            lux = read_light()
            now = time.time()
            accumulated_light += lux * (now - last_time)
            last_time = now

            print(f"현재 조도: {lux:.2f} lux | 누적 조도량: {accumulated_light:.2f}")

            if accumulated_light >= THRESH_ACC:
                print("충분한 광량 확보 → 회전합니다.")
                ok = rotate_180(direction, stop_event)
                if not ok:
                    break
                direction *= -1
                accumulated_light = 0

            # ? MEASURE_INTERVAL 동안에도 stop_event 빠르게 반응하도록 쪼개서 sleep
            sleep_left = MEASURE_INTERVAL
            while sleep_left > 0:
                if stop_event is not None and stop_event.is_set():
                    break
                t = 0.2 if sleep_left > 0.2 else sleep_left
                time.sleep(t)
                sleep_left -= t

    finally:
        # 종료 시 안전 정리
        _all_pins_off()
        # stop_event가 있으면 홈복귀도 시도 (원치 않으면 이 줄 빼면 됨)
        if stop_event is not None and stop_event.is_set():
            return_home(stop_event=None)  # 홈복귀는 끝까지 하도록 stop_event 무시

# -----------------------------
# 독립 실행 테스트
# -----------------------------
if __name__ == "__main__":
    return_home()
    rotate_loop()
