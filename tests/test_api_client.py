"""Tests for API client stop_reason capture."""

from unittest.mock import MagicMock, patch

from src.api_client import ApiClient
from src.models import ApiResponse


def _make_mock_response(text="hello", stop_reason="end_turn", input_tokens=10, output_tokens=5):
    resp = MagicMock()
    resp.content = [MagicMock(text=text)]
    resp.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    resp.stop_reason = stop_reason
    return resp


@patch("src.api_client.anthropic.Anthropic")
def test_call_captures_end_turn(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_mock_response(
        text='{"ok": true}', stop_reason="end_turn"
    )

    client = ApiClient(api_key="test-key")
    result = client.call(
        model="test-model", max_tokens=100, temperature=0,
        prompt="test", rate_limit_gap=0,
    )

    assert isinstance(result, ApiResponse)
    assert result.stop_reason == "end_turn"
    assert result.text == '{"ok": true}'


@patch("src.api_client.anthropic.Anthropic")
def test_call_captures_max_tokens(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_mock_response(
        text='{"truncated": "js', stop_reason="max_tokens"
    )

    client = ApiClient(api_key="test-key")
    result = client.call(
        model="test-model", max_tokens=100, temperature=0,
        prompt="test", rate_limit_gap=0,
    )

    assert result.stop_reason == "max_tokens"
