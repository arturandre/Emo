import numpy as np
from scipy.io import wavfile

# Load your mono .wav file
input_path = r'C:\Users\Artur Oliveira\projetosdev\emo_pers_robot\Diana\quem.wav'
output_path = r'C:\Users\Artur Oliveira\projetosdev\emo_pers_robot\Diana\quem2.wav'

# Read the sample rate and data
sample_rate, mono_data = wavfile.read(input_path)

# Ensure the input is mono
if len(mono_data.shape) > 2:
    raise ValueError("The input file is not mono.")
if len(mono_data.shape) == 2:
    mono_data = mono_data[0]

# Duplicate the mono data across 2 channels
four_channel_data = np.tile(mono_data, (2, 1)).T

# Save the 4-channel data to a new .wav file
wavfile.write(output_path, sample_rate, four_channel_data)

print(f"Converted {input_path} to 2-channel and saved as {output_path}")
