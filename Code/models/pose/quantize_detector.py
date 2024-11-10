import tensorflow as tf
import numpy as np

# Path to the extracted .tflite model file
extracted_model_path = r'C:\Users\Artur Oliveira\projetosdev\emo_pers_robot\Emo\Code\models\pose\pose_landmarks_detector.tflite'
quantized_model_path = r'C:\Users\Artur Oliveira\projetosdev\emo_pers_robot\Emo\Code\models\pose\pose_landmarks_detector_8bit.tflite'

# Load the model for conversion
converter = tf.lite.TFLiteConverter.from_saved_model(extracted_model_path) 

# Set optimizations and target specification for 8-bit integer quantization
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]

# Define representative dataset
def representative_data_gen():
    for _ in range(100):  # Generate 100 samples for calibration
        yield [np.random.rand(1, 256, 256, 3).astype(np.float32)]  # Adjust shape to match model input

converter.representative_dataset = representative_data_gen

# Convert the model to quantized format
quantized_tflite_model = converter.convert()

# Save the quantized model
with open(quantized_model_path, 'wb') as f:
    f.write(quantized_tflite_model)

print(f"Quantized model saved to: {quantized_model_path}")
