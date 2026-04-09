import os
import PIL.Image
import google.generativeai as genai
from config import GEMINI_API_KEY

# --- AI Setup ---
genai.configure(api_key=GEMINI_API_KEY, transport='rest')
ai_model = genai.GenerativeModel('models/gemini-2.5-flash')

def get_ai_analysis(alert_name, context, screenshot_path=None):
    """Use Gemini AI to generate troubleshooting steps based on text and visual dashboard data."""
    
    # Generic and flexible prompt for any dashboard layout
    prompt = (
        f"You are an expert Site Reliability Engineer (SRE).\n"
        f"Analyze the following incident using the provided context and the attached dashboard screenshot.\n\n"
        f"SYSTEM ALERT: {alert_name}\n"
        f"CONTEXT: {context}\n\n"
        "INSTRUCTIONS:\n"
        "1. Visual Inspection: Scan the screenshot for anomalies (RED/ORANGE panels or extreme spikes).\n"
        "2. Identification: Identify titles of problematic panels directly from the image text.\n"
        "3. Correlation: Determine if visual evidence confirms the alert or suggests a different root cause.\n"
        "4. Action Plan: Provide 3 professional troubleshooting steps based on this combined analysis."
    )
    
    try:
        # If a screenshot exists, perform multi-modal analysis (Vision + Text)
        if screenshot_path and os.path.exists(screenshot_path):
            img = PIL.Image.open(screenshot_path)
            response = ai_model.generate_content([prompt, img])
        else:
            # Fallback to text-only analysis if no image is available
            response = ai_model.generate_content(prompt)
            
        return response.text if response else "AI Analysis Failed."
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return "AI Service Unavailable or Visual Analysis Failed."
