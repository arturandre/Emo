import requests

url = 'https://dianaapi-543834107372.us-central1.run.app'
accessName='External-Dev'
key='cba401af31b045de4b45cfb82df9ffe62ecc2b99ca9edbc2aef1738868e3745a'
session = None
token = None
bearer_token = "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYXBpQ2FsbGVyIiwiYXVkIjoiZXh0ZXJuYWxVc2VyIiwiaXNzIjoiRGlhbmEgQVBJIiwiaWF0IjoxNzMwMDcxMDU2LCJleHAiOjE3MzE4MDgzMjgwMzN9.6vrAA41B8sqJzMhfWHALX-s5WkNmVq3hZIEg8z418QsHS6S0PiGskkqnJXOR57QUcJfYKQ5uVdDuWIgs6_UCmQ"
import requests

# URL and session ID
url = "https://dianaapi-543834107372.us-central1.run.app/audioIntent?session=202410280017f25fb095"

# Path to your .wav file
audio_path = r"C:\Users\Artur Oliveira\projetosdev\emo_pers_robot\Diana\quem4.wav"

# Open the .wav file in binary mode and make the request
with open(audio_path, 'rb') as audio_file:
    files = {
        'audioFile': (audio_path, audio_file, 'audio/wav')
    }
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {bearer_token}'
    }
    
    response = requests.post(url, headers=headers, files=files)

# Check if the request was successful
if response.status_code == 200:
    # Save the response as a .wav file
    with open("response.wav", "wb") as f:
        f.write(response.content)
    print("Response saved as response.wav")
else:
    print("Failed to get .wav file. Status Code:", response.status_code)
    print("Response:", response.text)
