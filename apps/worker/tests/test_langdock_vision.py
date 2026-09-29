"""Claude Vision OCR call: content shape and max_tokens retry-on-truncation."""

from unittest.mock import MagicMock

from app.langdock.client import LangdockClient


def _fake_response(text: str, stop_reason: str | None) -> MagicMock:
    response = MagicMock()
    response.content = [MagicMock(type="text", text=text)]
    response.usage = MagicMock(input_tokens=100, output_tokens=50)
    response.stop_reason = stop_reason
    return response


def test_extract_text_from_image_sends_image_and_prompt_blocks():
    client = LangdockClient()
    client._anthropic = MagicMock()
    client._anthropic.messages.create.return_value = _fake_response(
        "Erkannter Seiteninhalt", stop_reason="end_turn"
    )

    result = client.extract_text_from_image(b"\xff\xd8\xff\xe0fakejpeg", media_type="image/jpeg")

    assert result.text == "Erkannter Seiteninhalt"
    call_kwargs = client._anthropic.messages.create.call_args.kwargs
    content_blocks = call_kwargs["messages"][0]["content"]
    assert content_blocks[0]["type"] == "image"
    assert content_blocks[0]["source"]["media_type"] == "image/jpeg"
    assert content_blocks[1]["type"] == "text"
    client._anthropic.messages.create.assert_called_once()


def test_extract_text_from_image_retries_once_on_truncation():
    client = LangdockClient()
    client._anthropic = MagicMock()
    client._anthropic.messages.create.side_effect = [
        _fake_response("abgeschnittener Te", stop_reason="max_tokens"),
        _fake_response("vollstaendiger Text", stop_reason="end_turn"),
    ]

    result = client.extract_text_from_image(b"fakejpeg", max_tokens=100)

    assert result.text == "vollstaendiger Text"
    assert client._anthropic.messages.create.call_count == 2
    second_call_max_tokens = client._anthropic.messages.create.call_args_list[1].kwargs[
        "max_tokens"
    ]
    assert second_call_max_tokens == 200
