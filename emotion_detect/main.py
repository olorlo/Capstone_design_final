# main.py
# 스마트 화분 + 센서 + 표정 인식 통합 시스템 시작점

import socket
from emotion_detect.module1.camera_control import open_camera
from emotion_detect.module1.sensors import handle_sensor_data_with_socket


def setup_server():
    """클라이언트 연결 대기 및 소켓 반환"""
    HOST = ''
    PORT = 5000

    print("\n[Server] 소켓 서버 시작 중...")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)

    print(f"[Server] {PORT}번 포트에서 클라이언트 연결 대기 중...")
    conn, addr = server_socket.accept()
    print(f"[Server] ? {addr} 에서 연결됨")
    return conn, server_socket


def main():
    print("=== 스마트 화분 통합 시스템 시작 ===")

    # Picamera2 카메라 열기 (camera_control.py에서 구현)
    cam = open_camera()

    # 클라이언트 소켓 연결
    conn, server_socket = setup_server()

    try:
        # 센서 루프는 while True 내부에서 계속 돌아감.
        # ? 물 감지 시, sensors.py 안에서 emotion.run(cam) 이 호출되어
        #    10초 동안 표정 인식 + gTTS 음성 출력이 실행됨.
        handle_sensor_data_with_socket(cam, conn)
    except KeyboardInterrupt:
        print("\n[Main] 사용자 종료 감지")
    finally:
        print("[Main] 소켓 및 리소스 정리 중...")
        try:
            conn.close()
            server_socket.close()
        except Exception:
            pass
        print("[Main] 종료 완료")


if __name__ == "__main__":
    main()
