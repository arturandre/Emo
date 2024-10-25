import sounddevice as sd
import soundfile as sf

# Path to your .wav file
#wav_file = '/home/pi/Emo/Code/inmp441/PinkPanther60.wav'
#wav_file = '/home/pi/Emo/Code/audios/ohyeah-norm.wav'
wav_file = '/home/pi/Emo/Code/audios/wetoy-norm.wav'

# Read the .wav file (data and sample rate)
data, sample_rate = sf.read(wav_file)

# Set the volume factor (1.0 is original volume, 0.5 is half volume, etc.)
volume_factor = 0.1

# Adjust the volume by scaling the audio data
data = data * volume_factor

# Play the .wav file with adjusted volume
print(f"Playing {wav_file} at {volume_factor * 100}% volume")
sd.play(data, samplerate=sample_rate)
sd.wait()  # Wait until the file finishes playing
