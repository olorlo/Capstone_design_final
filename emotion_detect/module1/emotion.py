# emotion.py
# Picamera2와 Gemini API를 활용한 손자 컨셉 표정 인식 모듈 ?

import os
import cv2
import numpy as np
import onnxruntime as ort
import urllib.request
import time
from gtts import gTTS
import google.generativeai as genai
from emotion_detect.module1.camera_control import led
# ------------------------------------------------------------------
# 설정 및 환경 변수 로드
# ------------------------------------------------------------------

# SSH 터미널에서 설정한 환경 변수 읽기
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("?? [경고] GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
else:
    genai.configure(api_key=api_key)
    gemini_model = genai.GenerativeModel('gemini-2.5-flash')

MODEL_PATH = 'emotion6_model_fp16.onnx'
EMOTIONS = ['Angry', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral']

# 한글 감정 라벨 (Gemini 프롬프트용)
EMOTIONS_KO = {
    'Angry': '화남',
    'Fear': '두려움',
    'Happy': '기쁨',
    'Sad': '슬픔',
    'Surprise': '놀람',
    'Neutral': '평온함',
}

frontal_path = 'haarcascade_frontalface_default.xml'
profile_path = 'haarcascade_profileface.xml'

# ------------------------------------------------------------------
# Gemini AI 멘트 생성
# ------------------------------------------------------------------

def get_ai_comment(emotion_ko):
    """Gemini를 사용하여 손자 컨셉의 애교 섞인 멘트 생성"""
    if not api_key:
        return f"오늘 표정이 {emotion_ko}해 보이시네요!"

    prompt = f"""
    당신은 화분의 정령이자 사용자의 귀여운 손자입니다. 
    사용자의 현재 표정에서 느껴지는 감정은 '{emotion_ko}'입니다.
    이 상황에 맞춰 할머니/할아버지께 드리는 짧고 친근한 애교 섞인 한마디를 한국어로 해주세요.
    
    지침:
    1. 반드시 한 문장으로 짧게 답하세요.
    2. '했어용', '할머니/할아버지~' 등 손자가 재롱부리는 말투를 사용하세요.
    3. 감정에 공감하거나 기운을 북돋아 드리는 내용을 담으세요.
    """
    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[Gemini 오류] {e}")
        return f"할머니, 오늘 표정이 {emotion_ko}해 보이시네용! 제가 더 잘 자랄게용!"

# ------------------------------------------------------------------
# TTS 및 리소스 로드
# ------------------------------------------------------------------

def speak(text: str):
    """gTTS로 음성 생성 및 재생"""
    print(f"[AI 손자] {text}")
    try:
        tts = gTTS(text=text, lang='ko')
        tts.save("tts_emotion.mp3")
        # 시스템 설정에 따라 mpg123 또는 mpg321 선택
        os.system("mpg123 -q tts_emotion.mp3")
    except Exception as e:
        print(f"[TTS 오류] {e}")

def download_cascade(filename: str):
    url = f"https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/{filename}"
    if not os.path.exists(filename):
        print(f"? {filename} 다운로드 중...")
        try:
            urllib.request.urlretrieve(url, filename)
        except Exception as e:
            print(f"? 다운로드 실패: {e}")

def load_cascades():
    download_cascade(frontal_path)
    download_cascade(profile_path)
    return cv2.CascadeClassifier(frontal_path), cv2.CascadeClassifier(profile_path)

def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"? 모델 파일({MODEL_PATH})이 없습니다.")
    session = ort.InferenceSession(MODEL_PATH, providers=['CPUExecutionProvider'])
    input_name = session.get_inputs()[0].name
    return session, input_name

# ------------------------------------------------------------------
# 실행 로직
# ------------------------------------------------------------------

def run_emotion_10s_gtts(cam):
    """10초간 감지 후 Gemini 멘트 출력 및 결과 반환"""
    face_cascade, profile_cascade = load_cascades()
    try:
        session, input_name = load_model()
    except Exception as e:
        print(f"[모델 로드 오류] {e}")
        return None

    start_time = time.time()
    detected_emotion = None

    print("[Emotion] 3초 동안 표정 감지 시작...")

    while time.time() - start_time < 3:
        try:
            frame = cam.capture_array()
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            
            # 얼굴 찾기
            faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
            if len(faces) == 0:
                continue

            # 첫 번째 얼굴 분석
            (x, y, w, h) = faces[0]
            roi_gray = gray[y:y+h, x:x+w]
            roi_resized = cv2.resize(roi_gray, (48, 48)).astype("float32") / 255.0
            img_pixels = roi_resized.astype(np.float16)[None, :, :, None]

            prediction = session.run(None, {input_name: img_pixels})[0][0]
            detected_emotion = EMOTIONS[np.argmax(prediction)]
            print(f"? 감정 인식 성공: {detected_emotion}")
            led.off()
            break
        except Exception:
            continue

    # 멘트 생성 및 출력
    if detected_emotion:
        emo_ko = EMOTIONS_KO.get(detected_emotion, "평온함")
        msg = get_ai_comment(emo_ko)
        speak(msg)
    else:
        speak("할머니, 할아버지! 얼굴이 잘 안 보여요.")
    
    return detected_emotion

def run(cam):
    """외부(sensors.py) 호출용 인터페이스"""
    return run_emotion_10s_gtts(cam)
