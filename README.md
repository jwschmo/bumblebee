# Bumblebee

Bumblebee is an LLM driven home assistant.  Say the wake word "bumblebee" and ask any question you want to a local LLM model.  

Requires a valid API key for PicoVoice (https://picovoice.ai/)

## Local Installation

```
pip install -r requirements.txt
```

Copy one of the model.json.type files to model.json.  This file is used to set the prompt format and ban tokens, the default
is ChatML format so it should work with most recent models.  Set the llama_endpoint to point to your llama.cpp running
in server mode, if it's not on the same container/server as your SumBot service (see below!)

Copy sample.env to .env and put in your PicoVoice API key and the URL for your Bumblebee API (usually localhost port 3000)

## Running Bumblebee API

```
uvicorn main:app --host 0.0.0.0 --port 3000 --reload
```

## Running Bumblebee Voice App

```
python3 bumblebee.py
```

## Downloading an LLM model

We highly recommend OpenHermes 2.5 Mistral-7b fine tune for this task, as it's currently the best (Nov 2023) that
we've tested personally.  You can find different quantized versions of the model here:

https://huggingface.co/TheBloke/OpenHermes-2.5-Mistral-7B-GGUF/tree/main

I'd suggest the Q6 quant for GPU and Q4_K_M for CPU

## Running a model on llama.cpp in API mode

### Windows

Go to the llama.cpp releases and download either the win-avx2 package for CPU or the cublas for nvidia cards:

https://github.com/ggerganov/llama.cpp/releases

Extract the files out and run the following for nvidia GPUs:
```
server.exe -m <model>.gguf -t 4 -c 2048 -ngl 33 --host 0.0.0.0 --port 8086
```

For CPU only:
```
server.exe -m <model>.gguf -c 2048 --host 0.0.0.0 --port 8086
```

Replace <model> with whatever model you downloaded and put into the llama.cpp directory

### Linux, MacOS or WSL2
 
Follow the install instructions for llama.cpp at https://github.com/ggerganov/llama.cpp

Git clone, compile and run the following for GPU:
```
./server -m models/<model>.gguf -t 4 -c 2048 -ngl 33 --host 0.0.0.0 --port 8086
```

For CPU only:
```
./server -m models/<model>.gguf -c 2048 --host 0.0.0.0 --port 8086
```

Replace <model> with whatever model you downloaded and put into the llama.cpp/models directory

## Accessing API Directly for Testing

http://localhost:3000/docs
