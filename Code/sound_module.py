import sounddevice as sd
import soundfile as sf
import threading


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

    def _play_thread(self, clip_name):
        """Play the audio clip from memory."""
        if clip_name in self.audio_data:
            data, sample_rate = self.audio_data[clip_name]
            print(f"Playing {clip_name} from memory")
            with self.playing_lock:  # Ensure thread safety during playback
                sd.play(data, samplerate=sample_rate)
                sd.wait()  # Wait until the file finishes playing
        else:
            print(f"Audio clip {clip_name} not found in memory")

    def play_clip(self, clip_name):
        """Play the audio clip from memory."""
        if clip_name in self.audio_data:
            data, sample_rate = self.audio_data[clip_name]
            print(f"Playing {clip_name} from memory")
            play_thread = threading.Thread(target=self._play_thread, args=(clip_name,))
            play_thread.start() 
        else:
            print(f"Audio clip {clip_name} not found in memory")

# Example usage
if __name__ == "__main__":
    sound_module = SoundModule()  # Singleton instance
    sound_module.load_audio_clips()  # Preload all audio files into memory
    sound_module.play_clip('fart')  # Play an audio clip
    sound_module.play_clip('ohyeah')  # Play another audio clip
