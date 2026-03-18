# notifier.py
from gtts import gTTS
import tempfile, os
from pushbullet import Pushbullet
from config import PUSHBULLET_KEY

pb = Pushbullet(PUSHBULLET_KEY)

def play_tts(text):
    """TTS 음성 출력"""
    try:
        tts = gTTS(text=text, lang='ko')
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            os.system(f"mpg321 {fp.name} > /dev/null 2>&1")
            os.remove(fp.name)
    except Exception as e:
        print("[TTS] 오류:", e)

def push_message(title, message):
    """Pushbullet 알림 전송"""
    try:
        pb.push_note(title, message)
        print(f"[Pushbullet] {title} - 전송 완료")
    except Exception as e:
        print("[Pushbullet] 전송 실패:", e)
