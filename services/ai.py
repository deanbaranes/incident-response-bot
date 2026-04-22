import os
import PIL.Image
import google.generativeai as genai
import logging
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# AI Setup
genai.configure(api_key=GEMINI_API_KEY, transport="rest")
ai_model = genai.GenerativeModel("models/gemini-2.5-flash")


# Main function to send the incident details to Gemini
# It takes the alert context and an optional screenshot if we have one
def get_ai_analysis(alert_name, context, screenshot_path=None):
    """Analyze incident and generate troubleshooting steps using Gemini."""

    prompt = (
        f"You are a Site Reliability Engineer (SRE).\n"
        f"Analyze the following incident using the provided context and the attached dashboard screenshot.\n\n"
        f"SYSTEM ALERT: {alert_name}\n"
        f"CONTEXT: {context}\n\n"
        "INSTRUCTIONS:\n"
        "1. Visual Inspection: Scan the screenshot for anomalies (RED/ORANGE panels or extreme spikes).\n"
        "2. Identification: Identify titles of problematic panels directly from the image text.\n"
        "3. Correlation: Determine if visual evidence confirms the alert or suggests a different root cause.\n"
        "4. Action Plan: Provide 3 professional troubleshooting steps based on this combined analysis."
    )

    # Try to execute the AI request.
    # If a screenshot is provided, we send both the image and the text prompt together.
    try:
        if screenshot_path and os.path.exists(screenshot_path):
            img = PIL.Image.open(screenshot_path)
            response = ai_model.generate_content([prompt, img])
        else:
            response = ai_model.generate_content(prompt)

        return response.text if response else "AI Analysis failed."
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "AI Service unavailable or visual analysis failed."
