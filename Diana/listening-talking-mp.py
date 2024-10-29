import requests
import numpy as np
import sounddevice as sd
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import audio
from mediapipe.tasks.python.audio.core import audio_record
from scipy.io.wavfile import write

# Diana API endpoint
url = 'https://dianaapi-543834107372.us-central1.run.app'
accessName = 'External-Dev'
key = 'cba401af31b045de4b45cfb82df9ffe62ecc2b99ca9edbc2aef1738868e3745a'
session = None
token = None

# Function to create a session and retrieve token
def create_session():
    token_response = requests.get(url + '/token', params={'key': key, 'accessName': accessName})
    token = token_response.json().get('token')
    session_response = requests.get(url + '/session', headers={'Authorization': f'Bearer {token}'})
    session = session_response.json().get('session')
    print(f"Token: {token}")
    print(f"Session: {session}")
    return token, session

# Function to send .wav file to Diana API
def send_wav_to_api(wav_file, token, session):
    api_url = f"{url}/audioIntent?session={session}"
    with open(wav_file, 'rb') as audio_file:
        files = {'audioFile': (wav_file, audio_file, 'audio/wav')}
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.post(api_url, headers=headers, files=files)

    if response.status_code == 200:
        with open("response.wav", "wb") as f:
            f.write(response.content)
        print("Response saved as response.wav")
    else:
        print("Failed to get .wav response from API:", response.text)

# Initialize MediaPipe Audio Classifier for speech detection
def classify_audio_callback(result, timestamp_ms):
    global is_speaking, last_speech_time
    # Detects speech based on classifications with "speech" in category_name
    is_speaking = any("speech" in classification.category_name and classification.score > 0.6 
                      for classification in result.classifications[0].categories)
    if is_speaking:
        last_speech_time = time.time()

def init_audio_classifier():
    base_options = python.BaseOptions(model_asset_path="yamnet.tflite")
    options = audio.AudioClassifierOptions(
        base_options=base_options,
        running_mode=audio.RunningMode.AUDIO_STREAM,
        max_results=5,
        result_callback=classify_audio_callback,
    )
    return audio.AudioClassifier.create_from_options(options)

# Function to record audio and save as .wav
def record_to_wav(filename, sample_rate=16000, duration=1):
    """Records audio and appends to buffer if speech is detected."""
    global audio_buffer
    if is_speaking:
        audio_buffer.append(sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1))
    elif audio_buffer and (time.time() - last_speech_time) > 0.5:  # 500ms of silence
        # Concatenate all buffers, save to file, and clear buffer
        audio_data = np.concatenate(audio_buffer, axis=0)
        write(filename, sample_rate, audio_data.astype(np.int16))
        audio_buffer.clear()
        return True  # Indicates .wav is ready to send
    return False

# Main function to detect speech, record, and interact with Diana API
if __name__ == "__main__":
    # Initialize token and session
    token, session = create_session()

    # Initialize variables
    is_speaking = False
    last_speech_time = 0
    audio_buffer = []
    
    # Initialize audio classifier
    classifier = init_audio_classifier()
    classifier.start()  # Start MediaPipe audio stream

    # Start continuous audio recording and checking
    try:
        while True:
            wav_ready = record_to_wav("recorded_speech.wav")
            if wav_ready:
                # Send to API and get response if .wav is saved
                send_wav_to_api("recorded_speech.wav", token, session)
                # Optional: play response.wav here
    except KeyboardInterrupt:
        print("Process terminated.")
