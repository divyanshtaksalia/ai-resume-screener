import os
import io
import json
import PyPDF2
import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Backend is running!", "endpoint": "/screen-resume"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key
genai.configure(api_key="AIzaSyC2qJRfaBKfD_WPSxLcHmA1uUg5w2GJnHM")

def extract_text_from_pdf(file_bytes):
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in pdf_reader.pages:
        extracted = page.extract_text()
        if extracted: text += extracted
    return text

@app.post("/screen-resume")
async def screen_resume(job_description: str = Form(...), resume_file: UploadFile = File(...)):
    try:
        resume_bytes = await resume_file.read()
        resume_text = extract_text_from_pdf(resume_bytes)

        # FIX: Sabse pehle available models ki list check karte hain
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Priority: 1.5-flash > 1.0-pro > Jo bhi pehla mile
        model_to_use = "gemini-1.5-flash" 
        if "models/gemini-1.5-flash" in available_models:
            model_to_use = "gemini-1.5-flash"
        elif "models/gemini-pro" in available_models:
            model_to_use = "gemini-pro"
        else:
            # Agar dono nahi milte, toh list ka pehla model uthalo
            model_to_use = available_models[0].split('/')[-1]

        print(f"Using model: {model_to_use}") # Debugging ke liye terminal mein dikhega
        
        ai_model = genai.GenerativeModel(model_to_use)

        prompt = f"""
        Compare the Resume with the Job Description.
        JD: {job_description}
        Resume: {resume_text}
        Return ONLY a JSON object with:
        "match_score" (int), "matched_keywords" (list), "missing_skills" (list), "summary" (string)
        """

        response = ai_model.generate_content(prompt)
        
        # Clean response
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