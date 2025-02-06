from utils import call_openai_api

def fetch_user_stories_from_rally(rally_endpoint, rally_api_key):
    # Simulated fetch logic
    return ["User Story 1", "User Story 2", "User Story 3"]

def generate_code(user_story, language, prompt, openai_api_key):
    code_prompt = f"Generate {language} code for the following user story:\n\n{user_story}\n\nAdditional context:\n{prompt}"
    return call_openai_api(code_prompt, openai_api_key)
