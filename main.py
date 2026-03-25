import os
import io
import json
import PyPDF2
import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files aur templates setup
if not os.path.exists("templates"):
    os.makedirs("templates")

# Agar aapki CSS/JS files alag folder mein hain toh ise uncomment karein
# app.mount("/static", StaticFiles(directory="static"), name="static")

# API Key - Render Environment Variable se uthayega
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyC2qJRfaBKfD_WPSxLcHmA1uUg5w2GJnHM")
genai.configure(api_key=GEMINI_KEY)

def extract_text_from_pdf(file_bytes):
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in pdf_reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted
    return text

# Frontend Route: Browser mein URL kholte hi index.html dikhega
@app.get("/")
async def read_root():
    return FileResponse("templates/index.html")

# Backend Route: Resume screening ke liye
@app.post("/screen-resume")
async def screen_resume(job_description: str = Form(...), resume_file: UploadFile = File(...)):
    try:
        resume_bytes = await resume_file.read()
        resume_text = extract_text_from_pdf(resume_bytes)

        # Smart model selection
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        model_to_use = "gemini-1.5-flash" 
        if "models/gemini-1.5-flash" in available_models:
            model_to_use = "gemini-1.5-flash"
        elif "models/gemini-pro" in available_models:
            model_to_use = "gemini-pro"
        else:
            model_to_use = available_models[0].split('/')[-1]

        ai_model = genai.GenerativeModel(model_to_use)

        prompt = f"""
        Compare the Resume with the Job Description.
        JD: {job_description}
        Resume: {resume_text}
        Return ONLY a JSON object with:
        "match_score" (int), "matched_keywords" (list), "missing_skills" (list), "summary" (string)
        """

        response = ai_model.generate_content(prompt)
        res_text = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(res_text)

    except Exception as e:
        print(f"Detailed Error: {e}")
        return {
            "match_score": 0,
            "matched_keywords": ["Error"],
            "missing_skills": ["Check API/Model Access"],
            "summary": f"Could not reach Gemini: {str(e)}"
        }