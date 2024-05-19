import pvporcupine
import pvcheetah
import pvorca
import struct
import pyaudio
import requests
import num2words
import re
import os
import socketio
import asyncio
import webrtcvad
from dotenv import load_dotenv
import base64

# Load environment variables
load_dotenv()

pv_key = os.environ["PV_KEY"]
bb_api = os.environ["BB_API"]
pv_ww = os.environ["KEYWORD_FILE_PATH"]
pa_sample_rate = 16000
pa_frames_per_buffer_vad = 320  # 20ms frame for VAD
pa_frames_per_buffer_porcupine = 512  # Frame size for Porcupine

# Initialize WebSocket client
sio = socketio.AsyncClient()

# Parameters for WebRTC VAD
vad = webrtcvad.Vad()
vad.set_mode(3)  # Mode 3 is the most aggressive about filtering out non-speech

# Audio stream parameters
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

porcupine = pvporcupine.create(access_key=pv_key, keyword_paths=[pv_ww])
cheetah = pvcheetah.create(access_key=pv_key, endpoint_duration_sec=1)
orca = pvorca.create(access_key=pv_key)

pa = pyaudio.PyAudio()
input_stream_vad = pa.open(rate=pa_sample_rate, channels=1, format=pyaudio.paInt16, input=True, frames_per_buffer=pa_frames_per_buffer_vad)
input_stream_porcupine = pa.open(rate=pa_sample_rate, channels=1, format=pyaudio.paInt16, input=True, frames_per_buffer=pa_frames_per_buffer_porcupine)
output_stream = pa.open(rate=orca.sample_rate, channels=1, format=pyaudio.paInt16, output=True)

@sio.event
async def connect():
    print("Connected to server")

@sio.event
async def disconnect():
    print("Disconnected from server")

@sio.on('transcription')
async def on_transcription(data):
    print(f"Transcription: {data}")

def replace_numbers_in_string(s):
    return re.sub(r'\d+', lambda x: num2words.num2words(int(x.group())), s)

def convert_numbers(text):
    text = replace_numbers_in_string(text)
    text = text.replace("/", " per ")
    text = text.replace("&", " and ")
    text = text.replace("°", " degrees ")
    text = ''.join(c for c in text if c in orca.valid_characters)
    return text

def llm(text):
    params = {'input_prompt': text}
    response = requests.post(bb_api, params=params, headers={'accept': 'application/json'}, data='')
    response_data = response.json()
    return response_data["completion"]

def tts(text):
    text = text[:2000]  # TTS will only do 2k characters
    pcm = orca.synthesize(text)
    pcm = struct.pack('%dh' % len(pcm), *pcm)
    output_stream.write(pcm)

async def main():
    await sio.connect('http://localhost:5001')

    listening = False
    transcript = ""

    while True:
        try:
            pcm_vad = input_stream_vad.read(pa_frames_per_buffer_vad, exception_on_overflow=True)
            pcm_tuple_vad = struct.unpack_from("h" * pa_frames_per_buffer_vad, pcm_vad)
            pcm_bytes_vad = struct.pack('%dh' % len(pcm_tuple_vad), *pcm_tuple_vad)  # Convert tuple to bytes-like object

            pcm_porcupine = input_stream_porcupine.read(pa_frames_per_buffer_porcupine, exception_on_overflow=True)
            pcm_tuple_porcupine = struct.unpack_from("h" * pa_frames_per_buffer_porcupine, pcm_porcupine)
        except Exception as e:
            print(f"Error reading audio stream: {e}")
            continue

        try:
            if listening:
                try:
                    # Check if pcm_bytes is of correct length
                    if len(pcm_bytes_vad) != pa_frames_per_buffer_vad * 2:  # 2 bytes per sample (16-bit audio)
                        raise ValueError(f"pcm_bytes length {len(pcm_bytes_vad)} does not match expected length {pa_frames_per_buffer_vad * 2}")

                    # Log the pcm_bytes length and first few bytes for debugging
                    #print(f"pcm_bytes length: {len(pcm_bytes_vad)}")
                    #print(f"First few bytes of pcm_bytes: {pcm_bytes_vad[:10]}")

                    is_speech = vad.is_speech(pcm_bytes_vad, RATE)
                    if is_speech:
                        print("Speech detected, sending data to server")
                        await sio.emit("audio_data", base64.b64encode(pcm_bytes_vad).decode('utf-8'))
                except Exception as e:
                    print(f"Error during VAD processing: {e}")
                    continue

                try:
                    partial_transcript, is_endpoint = cheetah.process(pcm_tuple_porcupine)
                    if partial_transcript:
                        transcript += partial_transcript
                    if is_endpoint:
                        final_transcript = cheetah.flush()
                        transcript += final_transcript
                        print("Voice Input: " + transcript)
                        llm_response = llm(transcript)
                        print("LLM Output: " + llm_response)
                        tts(convert_numbers(llm_response))
                        transcript = ""
                        listening = False
                except Exception as e:
                    print(f"Error during Cheetah processing: {e}")
                    continue
            else:
                try:
                    keyword_index = porcupine.process(pcm_tuple_porcupine)
                    if keyword_index == 0:
                        print("Listening...")
                        listening = True
                except Exception as e:
                    print(f"Error during Porcupine processing: {e}")
        except Exception as e:
            print(f"Error while processing frame: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
    finally:
        input_stream_vad.stop_stream()
        input_stream_vad.close()
        input_stream_porcupine.stop_stream()
        input_stream_porcupine.close()
        output_stream.stop_stream()
        output_stream.close()
        pa.terminate()
        asyncio.run(sio.disconnect())
