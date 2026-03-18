# run.py (중요 수정본 + 성장일지 작성 후 5초 뒤 TTS)
import os
import cv2
import threading
import signal
import sys
import time
from collections import Counter
from itertools import islice
from ultralytics import YOLO
from plant_detect.module.rotating_pot import rotate_loop, return_home
import google.generativeai as genai

from picamera2 import Picamera2
from libcamera import Transform

from tts_utils import extract_summary, speak_ko

try:
    from plant_detect.module.pushbullet_utils import send_push_note, send_push_file, PushbulletError
except ImportError:
    from pyshbullet_utils import send_push_note, send_push_file, PushbulletError

SHOW_WINDOW = False
TARGET_LABEL_COUNT = 10
SAVE_FIRST_FRAME_PATH = "saved_frame.jpg"
SAVE_FIRST_ANN_PATH = "saved_frame_annotated.jpg"
MODEL_PATH = "best1.pt"

API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("환경변수 GOOGLE_API_KEY 가 설정되지 않았습니다.")
genai.configure(api_key=API_KEY)

GEMINI_MODEL_NAME = "gemini-2.5-flash"
gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)

# ===== 전역 종료 플래그/리소스 =====
stop_event = threading.Event()
picam = None
rotate_thread = None


def cleanup():
    """종료/재시작 시 리소스 정리"""
    global picam, rotate_thread

    # 회전 루프 중지
    stop_event.set()

    if rotate_thread is not None and rotate_thread.is_alive():
        rotate_thread.join(timeout=2)

    # 카메라 정지
    if picam is not None:
        try:
            picam.stop()
        except Exception:
            pass
        picam = None

    # 창 닫기
    if SHOW_WINDOW:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

    # 홈 복귀
    try:
        return_home()
    except Exception:
        pass


def handle_sigterm(signum, frame):
    print(f"\n[종료 신호] signum={signum} 수신 → 정리 후 종료합니다.")
    cleanup()
    sys.exit(0)


def main():
    global picam, rotate_thread

    # SIGTERM/SIGINT 처리 등록 (client.py terminate 대응)
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

    # 시작 시 stop_event 초기화
    stop_event.clear()

    # 홈 위치로 복귀
    return_home()

    # ===== YOLO 로드 =====
    yolo_model = YOLO(MODEL_PATH)

    # ===== Picamera2 설정 =====
    picam = Picamera2()
    config = picam.create_preview_configuration(
        main={"size": (1280, 720), "format": "RGB888"},
        transform=Transform()
    )
    picam.configure(config)
    picam.start()

    labels = []
    saved_frame_written = False

    print("라벨 수집을 시작합니다. (SIGTERM 오면 즉시 종료/재시작 가능)")
    try:
        while (len(labels) < TARGET_LABEL_COUNT) and (not stop_event.is_set()):
            frame = picam.capture_array()
            results = yolo_model(frame, verbose=False)

            if results and len(results) > 0 and getattr(results[0], "boxes", None) is not None:
                for box in results[0].boxes:
                    cls = int(box.cls[0])
                    label = yolo_model.names.get(cls, str(cls))
                    labels.append(label)

            if not saved_frame_written:
                try:
                    cv2.imwrite(SAVE_FIRST_FRAME_PATH, frame)
                    if results and len(results) > 0:
                        annotated0 = results[0].plot()
                        cv2.imwrite(SAVE_FIRST_ANN_PATH, annotated0)
                    print(f"프레임 저장 완료: {SAVE_FIRST_FRAME_PATH}, {SAVE_FIRST_ANN_PATH}")
                except Exception as e:
                    print(f"[저장 경고] 첫 프레임 저장 실패: {e}")
                saved_frame_written = True

            if SHOW_WINDOW and results and len(results) > 0:
                annotated = results[0].plot()
                cv2.imshow("YOLO + Picamera2", annotated)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

            if labels:
                print(f"Detected Labels (count={len(labels)}): {labels[-5:]} ...")

    finally:
        # 여기서도 정리(정상 루프 종료든, SIGTERM이든 안전)
        try:
            if picam is not None:
                picam.stop()
        except Exception:
            pass
        picam = None

        if SHOW_WINDOW:
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass

    # stop_event가 켜진 상태면(재시작/종료) 성장일지까지 가지 말고 종료
    if stop_event.is_set():
        print("[중단] stop_event 감지 → 성장일지/회전 생략하고 종료")
        cleanup()
        return

    # ===== 라벨 정리 및 성장일지 =====
    if labels:
        counts = Counter(labels)
        top_labels = [k for k, _ in islice(counts.most_common(5), 5)]
    else:
        top_labels = []

    print("\n--- 성장일지 작성 시작 ---")
    if top_labels:
        levels_str = ", ".join(top_labels)
        prompt = (
            f"YOLO로 방울토마토의 성장 단계를 {levels_str}와 같이 감지했어. "
            f"이 결과를 바탕으로 방울토마토의 현재 성장 상태를 통합하여 3줄짜리 성장일지를 작성해줘. "
            f"레벨별로 구분하지 말고, 전체적인 성장 상태만 설명해줘. "
            f"작성 결과는 독거노인에게 전송될 예정이니 귀여운 손자 컨셉으로 가줘. "
            f"칭찬과 격려의 말을 꼭 포함해줘. "
            f"위 성장일지 한줄로 요약해줘. 특수 문자 제거해주고 이모티콘은 빼줘 "
        )

        try:
            response = gemini_model.generate_content(prompt)
            text = getattr(response, "text", "") or ""
            print("\n[방울토마토 종합 성장일지]")
            print(text)

            summary_line = extract_summary(text)

            if summary_line:
                # ? 성장일지 작성 후 5초 뒤 TTS
                delay = 3
                print(f"\n[TTS] {delay:.0f}초 뒤에 출력합니다...")
                slept = 0.0
                while slept < delay:
                    if stop_event.is_set():
                        print("[TTS 취소] stop_event 감지")
                        break
                    time.sleep(0.1)
                    slept += 0.1

                if not stop_event.is_set():
                    print("[TTS]")
                    print(summary_line)
                    speak_ko(summary_line)
            else:
                print("\n[요약 추출 실패] 응답 형식을 확인하세요.")

            # === Pushbullet 전송 ===
            try:
                send_push_note(title="[방울토마토 종합 성장일지]", body=text)
                send_push_file(
                    title="[방울토마토 첫 프레임]",
                    body="금일 저장된 프레임을 첨부합니다.",
                    filepath=SAVE_FIRST_FRAME_PATH,
                )
            except PushbulletError as pe:
                print(f"[Pushbullet 오류] {pe}")

        except Exception as e:
            print(f"\n[오류] 성장일지 생성 중 문제가 발생했습니다: {e}")
    else:
        print("감지된 라벨이 없어 성장일지를 작성할 수 없습니다.")

    print("\n--- 성장일지 작성 완료 ---")

    # ===== 회전은 쓰레드로 돌리고, stop_event로 멈출 수 있게 =====
    rotate_thread = threading.Thread(target=rotate_loop, args=(stop_event,), daemon=True)
    rotate_thread.start()

    # run.py가 종료되지 않도록 대기(rotate_loop가 계속 돌게)
    try:
        while not stop_event.is_set():
            signal.pause()
    except Exception:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()
