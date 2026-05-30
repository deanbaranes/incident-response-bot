from unittest.mock import patch, MagicMock
from services.ai import get_ai_analysis


@patch("services.ai.ai_model.generate_content")
def test_get_ai_analysis_text_only(mock_generate_content):
    """Test AI analysis when no screenshot is provided."""
    mock_response = MagicMock()
    mock_response.text = "Here is the text analysis."
    mock_generate_content.return_value = mock_response

    result = get_ai_analysis("High CPU", "Context data")

    # generate_content should be called with just a string prompt
    mock_generate_content.assert_called_once()
    args, kwargs = mock_generate_content.call_args
    assert isinstance(args[0], str)
    assert result == "Here is the text analysis."


@patch("services.ai.ai_model.generate_content")
def test_get_ai_analysis_fallback_on_exception(mock_generate_content):
    """Test AI analysis graceful degradation on API exception."""
    mock_generate_content.side_effect = Exception("API is down")

    result = get_ai_analysis("High CPU", "Context data")

    assert result == "AI Service unavailable or analysis failed."


@patch("services.ai.ai_model.generate_content")
def test_get_ai_analysis_empty_response(mock_generate_content):
    """Test AI analysis fallback when response text is empty or None."""
    mock_response = MagicMock()
    # Simulate a response object that has empty text
    mock_response.text = ""
    mock_generate_content.return_value = mock_response

    result = get_ai_analysis("High CPU", "Context data")

    # It should not crash, it should just return the empty string or fallback safely.
    assert result == ""
