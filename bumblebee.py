import pvporcupine
import pvcheetah
import pvorca
import struct
import pyaudio
import requests
import num2words
import re
import os

# Nice way to load environment variables for deployments
from dotenv import load_dotenv
load_dotenv()

pv_key = os.environ["PV_KEY"]
bb_api = os.environ["BB_API"]

porcupine = pvporcupine.create(access_key=pv_key, keywords=['bumblebee'])
cheetah = pvcheetah.create(access_key=pv_key, endpoint_duration_sec=1)
orca = pvorca.create(access_key=pv_key)
print(orca.valid_characters)

pa = pyaudio.PyAudio()
input_stream = pa.open(rate=cheetah.sample_rate, channels=1, format=pyaudio.paInt16, input=True, frames_per_buffer=cheetah.frame_length)
outut_stream = pa.open(rate=orca.sample_rate, channels=1, format=pyaudio.paInt16, output=True)

def replace_numbers_in_string(s):
     return re.sub(r'\d+', lambda x: num2words.num2words(int(x.group())), s)

def convert_numbers(text):
    text = replace_numbers_in_string(text)
    text = text.replace("/", " per ")
    text = text.replace("&", " and ")
    text = text.replace("°", " degrees ")
    text = ''.join(c for c in text if c in orca.valid_characters)
    return text

# Call the LLM API service and get the completion out
def llm(text):
    params = {'input_prompt': text}
    response = requests.post(bb_api, params=params, headers={'accept': 'application/json'}, data='')
    response_data = response.json()
    return response_data["completion"]

# Send that audio out the speakers
def tts(text):
    text = text[:2000] # TTS will only do 2k characters
    pcm = orca.synthesize(text)
    pcm = struct.pack('%dh' % len(pcm), *pcm)
    outut_stream.write(pcm)

listening = False
transcript = ""
while True:
    # Record audio from mic
    pcm = input_stream.read(cheetah.frame_length, exception_on_overflow = True)
    pcm = struct.unpack_from("h" * cheetah.frame_length, pcm)

    # Do speech to text, when done listening go back to wake word
    if listening:
        partial_transcript, is_endpoint = cheetah.process(pcm)
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

    # Do wake word detection and start listening for speech to text
    else:
        keyword_index = porcupine.process(pcm)
        if keyword_index == 0:
            print("Listening...")
            listening = True
