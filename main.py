from fastapi import FastAPI
import json
import requests

# Load the llm config from the json file provided on command line
with open("model.json", 'r') as file:
    model = json.load(file)

# Whip the llama into gear
DEFAULT_SYSTEM = "You are Bumblebee, a friendly chatbot. You help the user answer questions, solve problems and make plans. You waste no words and provide the shortest answer possible without punctuation"
DEFAULT_TOKENS = -1
DEFAULT_TEMP = 0.7

# Fast API init
app = FastAPI(
        title="BumbleBee API",
        description="Just another way to call llama.cpp in server mode",
        version="1.0",
        contact={
            "name": "Pat Wendorf",
            "email": "pat.wendorf@mongodb.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/license/mit/",
    }
)

# Endpoint to compare 2 images by URL and show similarity
@app.post("/llm")
async def llm(input_prompt: str):

    # Build the prompt
    prompt = model["prompt_format"].replace("{system}", DEFAULT_SYSTEM)
    prompt = prompt.replace("{prompt}", input_prompt)

    api_data = {
        "prompt": prompt,
        "n_predict": DEFAULT_TOKENS,
        "temperature": DEFAULT_TEMP,
        "stop": model["stop_tokens"],
        "tokens_cached": 0
    }

    # Time the process
    try:
        # Call the model API
        response = requests.post(model["llama_endpoint"], headers={"Content-Type": "application/json"}, json=api_data)
        json_output = response.json()
        output = {"completion": json_output['content']}
    except:
        output = {"error": "My AI model is not responding try again in a moment 🔥🐳"}

    # remove annoying formatting in output
    return output
