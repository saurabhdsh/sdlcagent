import PyPDF2
from io import BytesIO
from utils import call_openai_api
import openai

def handle_file_upload(file, model="gpt-4"):
    try:
        if file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(BytesIO(file.read()))
            file_content = "\n".join(page.extract_text() for page in pdf_reader.pages if page.extract_text())
        else:
            file_content = file.read().decode("utf-8")

        prompt = f"Generate a user story based on the following document:\n\n{file_content}"
        openai.api_key = config.get("openai_api_key")
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except UnicodeDecodeError:
        return "File uploaded successfully, but it couldn't be decoded. Please ensure it is a valid text or PDF file."
    except Exception as e:
        return f"An error occurred: {str(e)}"
