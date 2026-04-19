import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock


def _gemini_resp(text="AI analysis result"):
    resp = MagicMock()
    resp.text = text
    return resp


class TestGetAiAnalysis:
    def test_returns_text_from_gemini(self):
        from services import ai as ai_mod
        with patch.object(ai_mod.ai_model, "generate_content", return_value=_gemini_resp("Step 1")):
            result = ai_mod.get_ai_analysis("HighCPUUsage", "CPU at 94%")
            assert result == "Step 1"

    def test_instruction_injected_into_prompt(self):
        from services import ai as ai_mod
        with patch.object(ai_mod.ai_model, "generate_content", return_value=_gemini_resp()) as mock_gen:
            ai_mod.get_ai_analysis("HighCPUUsage", "context", instruction="Focus on memory leaks")
            prompt_arg = mock_gen.call_args[0][0]
            assert "Focus on memory leaks" in prompt_arg

    def test_no_instruction_omits_playbook_block(self):
        from services import ai as ai_mod
        with patch.object(ai_mod.ai_model, "generate_content", return_value=_gemini_resp()) as mock_gen:
            ai_mod.get_ai_analysis("HighCPUUsage", "context", instruction=None)
            prompt_arg = mock_gen.call_args[0][0]
            assert "PLAYBOOK INSTRUCTION" not in prompt_arg

    def test_text_only_call_when_no_screenshot(self):
        from services import ai as ai_mod
        with patch.object(ai_mod.ai_model, "generate_content", return_value=_gemini_resp()) as mock_gen:
            ai_mod.get_ai_analysis("HighCPUUsage", "context")
            call_arg = mock_gen.call_args[0][0]
            assert isinstance(call_arg, str)

    def test_image_included_when_screenshot_exists(self):
        from services import ai as ai_mod
        with patch.object(ai_mod.ai_model, "generate_content", return_value=_gemini_resp()) as mock_gen, \
             patch("services.ai.PIL.Image.open", return_value=MagicMock()):
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                f.write(b"fake png")
                tmp = f.name
            try:
                ai_mod.get_ai_analysis("HighCPUUsage", "context", screenshot_path=tmp)
                call_arg = mock_gen.call_args[0][0]
                assert isinstance(call_arg, list) and len(call_arg) == 2
            finally:
                os.unlink(tmp)

    def test_gemini_exception_returns_fallback(self):
        from services import ai as ai_mod
        with patch.object(ai_mod.ai_model, "generate_content", side_effect=Exception("quota")):
            result = ai_mod.get_ai_analysis("HighCPUUsage", "context")
            assert "unavailable" in result.lower() or "failed" in result.lower()

    def test_none_response_returns_fallback(self):
        from services import ai as ai_mod
        with patch.object(ai_mod.ai_model, "generate_content", return_value=None):
            result = ai_mod.get_ai_analysis("HighCPUUsage", "context")
            assert "failed" in result.lower()

    def test_alert_name_in_prompt(self):
        from services import ai as ai_mod
        with patch.object(ai_mod.ai_model, "generate_content", return_value=_gemini_resp()) as mock_gen:
            ai_mod.get_ai_analysis("DiskSpaceLow", "disk at 95%")
            prompt_arg = mock_gen.call_args[0][0]
            assert "DiskSpaceLow" in prompt_arg
