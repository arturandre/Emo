import sounddevice as sd
import soundfile as sf
import threading
import subprocess

class SoundModule:
    _instance = None  # Singleton instance

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SoundModule, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):  # Prevent re-initialization
            self.audio_data = {}  # Store audio data and sample rates
            self.playing_lock = threading.Lock()  # Lock for playing sounds
            self.initialized = True

    def load_audio_clips(self):
        """Load all audio clips into memory."""
        audio_clips = {
            'wetoy': ('/home/pi/Emo/Code/audios/wetoy-norm.wav', 0.1),
            'ohyeah': ('/home/pi/Emo/Code/audios/ohyeah-norm.wav', 0.1),
            'ohno': ('/home/pi/Emo/Code/audios/ohno-norm.wav', 0.1),
            'fart': ('/home/pi/Emo/Code/audios/732055__blubberfreak__blubberfreak-fart-1.wav', 0.5),
        }

        for name, (path, volume_factor) in audio_clips.items():
            # Read and cache audio files
            try:
                data, sample_rate = sf.read(path)
                data *= volume_factor  # Adjust volume
                self.audio_data[name] = (data, sample_rate)
            except FileNotFoundError:
                print(f"Error: The file {path} was not found.")
            except Exception as e:
                print(f"An error occurred while loading the sound file: {e}")

    def _play_clip(self, clip_name):
        """Play the audio clip from memory."""
        with self.playing_lock:  # Ensure thread safety during playback
            if clip_name in self.audio_data:
                data, sample_rate = self.audio_data[clip_name]
                print(f"Playing {clip_name} from memory")
                sd.play(data, samplerate=sample_rate)
                sd.wait()  # Wait until the file finishes playing
            else:
                print(f"Audio clip {clip_name} not found in memory")

    def play_clip(self, clip_name):
        """Play the audio clip from memory."""
        if clip_name in self.audio_data:
            play_thread = threading.Thread(target=self._play_clip, args=(clip_name,))
            play_thread.start() 
        else:
            print(f"Audio clip {clip_name} not found in memory")

    def speak_oh_yeah(self):
        self.speak("oh yeah")

    def speak_oh_no(self):
        self.speak("oh noo")

    def speak_dancing_time(self):
        self.speak("Eh, hora, de!")
        self.speak("dançar!")

    def speak_danger(self):
        self.speak("Eh, hora, de!")
        self.speak("dançar!", volume=200)

    def speak_danger(self):
        self.speak("Perigo! Perigo! Perigo!", speed=100, pitch=80)

    def speak_ping(self):
        self.speak("Ping", speed=200, pitch=99, voice="f1")

    def speak_pong(self):
        self.speak("Pong", speed=80, pitch=0)

    def _speak(self, text, volume=100, speed=80, pitch=0, voice="m1"):
        with self.playing_lock:
            try:
                print(f"Speaking: {text}")
                subprocess.run(['espeak',
                                '-p', str(pitch), # pitch
                                f'-vpt+{voice}', # speaker template
                                text,
                                '-s', str(speed), # speed (80~280),
                                '-a', str(volume),
                                ], stderr=subprocess.DEVNULL,  # Suppress error output
                                check=True)
            except Exception as e:
                print(f"An error occurred with espeak: {e}")

    def speak(self, text, volume=100, speed=80, pitch=0, voice="m1"):
        """Use espeak to synthesize speech."""
        play_thread = threading.Thread(target=self._speak, args=((text, volume, speed, pitch, voice)))
        play_thread.start()


# Example usage
if __name__ == "__main__":
    sound_module = SoundModule()  # Singleton instance
    sound_module.load_audio_clips()  # Preload all audio files into memory
    sound_module.play_clip('fart')  # Play an audio clip
    sound_module.play_clip('ohyeah')  # Play another audio clip
    #espeak -p 0 -vpt+m1 "oh noo" -s 80
