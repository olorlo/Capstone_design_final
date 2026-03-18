# pushbullet_utils.py
import os
from typing import Optional
from pushbullet import Pushbullet

class PushbulletError(RuntimeError):
    pass

def _get_pb(api_key: Optional[str] = None) -> Pushbullet:
    key = api_key or os.environ.get("PUSHBULLET_API_KEY")
    if not key:
        raise PushbulletError("Pushbullet API 키가 없습니다. api_key 인자 또는 환경변수 PUSHBULLET_API_KEY를 설정하세요.")
    try:
        return Pushbullet(key)
    except Exception as e:
        raise PushbulletError(f"Pushbullet 초기화 실패: {e}")

def _find_device(pb: Pushbullet, device_nick: Optional[str]):
    if not device_nick:
        return None
    try:
        for d in pb.devices:
            if getattr(d, "nickname", None) == device_nick:
                return d
        raise PushbulletError(f"'{device_nick}' 이름의 디바이스를 찾지 못했습니다. Pushbullet 앱에서 디바이스 닉네임을 확인하세요.")
    except Exception as e:
        raise PushbulletError(f"디바이스 조회 실패: {e}")

def send_push_note(
    title: str,
    body: str,
    api_key: Optional[str] = None,
    device_nick: Optional[str] = None,
) -> None:
    """
    간단한 텍스트 노트 푸시.
    - api_key 미지정 시 환경변수 PUSHBULLET_API_KEY 사용
    - device_nick 지정 시 해당 디바이스로만 전송 (없으면 모든 기기에 브로드캐스트)
    """
    pb = _get_pb(api_key)
    device = _find_device(pb, device_nick)
    try:
        if device:
            pb.push_note(title, body, device=device)
        else:
            pb.push_note(title, body)
        print("[Pushbullet] 노트 전송 완료")
    except Exception as e:
        raise PushbulletError(f"노트 전송 실패: {e}")

def send_push_file(
    title: str,
    body: str,
    filepath: str,
    api_key: Optional[str] = None,
    device_nick: Optional[str] = None,
) -> None:
    """
    파일(이미지 등)을 첨부해서 푸시.
    """
    if not os.path.isfile(filepath):
        raise PushbulletError(f"파일이 존재하지 않습니다: {filepath}")

    pb = _get_pb(api_key)
    device = _find_device(pb, device_nick)

    try:
        with open(filepath, "rb") as f:
            file_data = pb.upload_file(f, os.path.basename(filepath))
        if device:
            pb.push_file(device=device, title=title, body=body, **file_data)
        else:
            pb.push_file(title=title, body=body, **file_data)
        print(f"[Pushbullet] 파일 전송 완료: {filepath}")
    except Exception as e:
        raise PushbulletError(f"파일 전송 실패: {e}")
