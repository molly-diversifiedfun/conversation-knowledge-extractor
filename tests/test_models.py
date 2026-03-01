"""Tests for data models."""

from src.models import ApiResponse


def test_api_response_includes_stop_reason():
    resp = ApiResponse(
        text="hello",
        input_tokens=10,
        output_tokens=5,
        stop_reason="end_turn",
    )
    assert resp.stop_reason == "end_turn"
    assert resp.text == "hello"


def test_api_response_is_frozen():
    resp = ApiResponse(text="hi", input_tokens=1, output_tokens=1, stop_reason="end_turn")
    try:
        resp.text = "changed"
        assert False, "Should have raised FrozenInstanceError"
    except AttributeError:
        pass


def test_api_response_max_tokens_stop_reason():
    resp = ApiResponse(
        text='{"partial": "json',
        input_tokens=100,
        output_tokens=4096,
        stop_reason="max_tokens",
    )
    assert resp.stop_reason == "max_tokens"
