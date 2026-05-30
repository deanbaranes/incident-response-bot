import google.generativeai as genai
import logging
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# AI Setup
genai.configure(api_key=GEMINI_API_KEY, transport="rest")
ai_model = genai.GenerativeModel("models/gemini-2.5-flash")


# Main function to send the incident details to Gemini
# It takes the alert context and optional playbook instructions.
def get_ai_analysis(alert_name, context, instruction=None):
    """Analyze incident and generate troubleshooting steps using Gemini based on metrics alone."""

    # Add playbook instructions to prompt if available
    extra = f"\nPLAYBOOK INSTRUCTION:\n{instruction}\n" if instruction else ""

    prompt = (
        f"You are a Site Reliability Engineer (SRE).\n"
        f"Analyze the following incident using the provided context and metrics.\n"
        f"{extra}\n"
        f"SYSTEM ALERT: {alert_name}\n"
        f"CONTEXT:\n{context}\n\n"
        "INSTRUCTIONS:\n"
        "1. Metric Analysis: Analyze the provided metric values and determine if they indicate a critical issue.\n"
        "2. Correlation: Determine how the metrics correlate with the system alert.\n"
        "3. Action Plan: Provide 3 professional troubleshooting steps based on this analysis."
    )

    # Try to execute the AI request.
    try:
        response = ai_model.generate_content(prompt)
        return response.text if response else "AI Analysis failed."
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "AI Service unavailable or analysis failed."
