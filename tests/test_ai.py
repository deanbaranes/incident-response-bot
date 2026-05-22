from unittest.mock import patch, MagicMock
from services.ai import get_ai_analysis


@patch("services.ai.ai_model.generate_content")
def test_get_ai_analysis_text_only(mock_generate_content):
    """Test AI analysis when no screenshot is provided."""
    mock_response = MagicMock()
    mock_response.text = "Here is the text analysis."
    mock_generate_content.return_value = mock_response

    result = get_ai_analysis("High CPU", "Context data", screenshot_path=None)

    # generate_content should be called with just a string prompt
    mock_generate_content.assert_called_once()
    args, kwargs = mock_generate_content.call_args
    assert isinstance(args[0], str)
    assert result == "Here is the text analysis."


@patch("services.ai.PIL.Image.open")
@patch("services.ai.os.path.exists")
@patch("services.ai.ai_model.generate_content")
def test_get_ai_analysis_with_screenshot(mock_generate_content, mock_exists, mock_open):
    """Test AI analysis when a valid screenshot is provided."""
    mock_exists.return_value = True
    mock_img = MagicMock()
    mock_open.return_value = mock_img

    mock_response = MagicMock()
    mock_response.text = "Here is the visual analysis."
    mock_generate_content.return_value = mock_response

    result = get_ai_analysis("High CPU", "Context data", screenshot_path="dummy.png")

    # generate_content should be called with a list: [prompt, img]
    mock_generate_content.assert_called_once()
    args, kwargs = mock_generate_content.call_args
    assert isinstance(args[0], list)
    assert len(args[0]) == 2
    assert args[0][1] == mock_img
    assert result == "Here is the visual analysis."


@patch("services.ai.ai_model.generate_content")
def test_get_ai_analysis_fallback_on_exception(mock_generate_content):
    """Test AI analysis graceful degradation on API exception."""
    mock_generate_content.side_effect = Exception("API is down")

    result = get_ai_analysis("High CPU", "Context data")

    assert result == "AI Service unavailable or visual analysis failed."
