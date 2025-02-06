import os
import openai

config = {
    "openai_api_key": os.getenv("OPENAI_API_KEY"),
    "rally_endpoint": os.getenv("RALLY_ENDPOINT"),
    "rally_api_key": os.getenv("RALLY_API_KEY"),
}

def call_openai_api(prompt, api_key):
    openai.api_key = api_key
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150
    )
    return response.choices[0].text.strip()

def check_rally_config():
    return bool(config.get("rally_endpoint") and config.get("rally_api_key"))

def upload_user_story_to_rally(user_story, rally_endpoint, rally_api_key):
    # Simulated Rally upload logic
    return f"User story uploaded to {rally_endpoint}"
