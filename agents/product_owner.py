import PyPDF2
from io import BytesIO
from utils import call_openai_api

def handle_file_upload(uploaded_file, openai_api_key):
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
            file_content = "\n".join(page.extract_text() for page in pdf_reader.pages if page.extract_text())
        else:
            file_content = uploaded_file.read().decode("utf-8")

        prompt = f"Generate a user story based on the following document:\n\n{file_content}"
        return call_openai_api(prompt, openai_api_key)
    except UnicodeDecodeError:
        return "File uploaded successfully, but it couldn't be decoded. Please ensure it is a valid text or PDF file."
    except Exception as e:
        return f"An error occurred: {str(e)}"
