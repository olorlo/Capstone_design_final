# client.py
import socket
import subprocess
import os
import signal
import time

HOST = '192.168.137.116'
PORT = 5000

run_proc = None  # 현재 실행 중인 run.py 프로세스 핸들

def stop_run_script():
    global run_proc
    if run_proc is None:
        return

    # 아직 살아있으면 종료 시도
    if run_proc.poll() is None:
        print("[중지] 기존 run.py 종료 요청(terminate)...")
        try:
            run_proc.terminate()  # SIGTERM
            run_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("[중지] terminate로 안 꺼져서 kill...")
            run_proc.kill()
            run_proc.wait(timeout=3)
        except Exception as e:
            print(f"[중지 오류] {e}")

    run_proc = None
    print("[중지] 기존 run.py 종료 완료")

def start_run_script():
    global run_proc
    print("[실행] run.py를 새로 실행합니다...")
    # 필요하면 cwd 지정 가능: cwd="/home/pi/project"
    run_proc = subprocess.Popen(["python3", "run.py"])

def restart_run_script():
    stop_run_script()
    start_run_script()

def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))

    try:
        while True:
            data = client_socket.recv(1024).decode(errors="ignore").strip()
            if not data:
                break

            print("서버 메시지:", data)

            if data.lower() == "run":
                restart_run_script()
                client_socket.sendall("run.py 재시작 완료".encode())
            elif data.lower() == "stop":
                stop_run_script()
                client_socket.sendall("run.py 중지 완료".encode())
            else:
                print(f"[무시] 인식하지 못한 명령: {data}")
                client_socket.sendall("알 수 없는 명령입니다.".encode())

    except Exception as e:
        print(f"[에러] {e}")
    finally:
        # 클라이언트 종료 시 run.py도 같이 정리
        stop_run_script()
        client_socket.close()

if __name__ == "__main__":
    main()
