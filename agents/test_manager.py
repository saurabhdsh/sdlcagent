from utils import call_openai_api

def generate_test_cases(user_story, prompt, openai_api_key):
    test_case_prompt = f"Generate test cases for the following user story:\n\n{user_story}\n\nAdditional context:\n{prompt}"
    return call_openai_api(test_case_prompt, openai_api_key)
