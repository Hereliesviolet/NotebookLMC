"""Honest status for sources that parse without error but yield 0 chunks."""

from types import SimpleNamespace

from app.jobs.status import NO_CONTENT_MESSAGE, mark_source_no_content


class _FakeSession:
    def commit(self) -> None:
        pass


def test_mark_source_no_content_sets_status_and_message():
    source = SimpleNamespace(status="processing", error_message=None)

    mark_source_no_content(_FakeSession(), source)

    assert source.status == "no_content"
    assert source.error_message == NO_CONTENT_MESSAGE


def test_mark_source_no_content_overwrites_previous_error():
    source = SimpleNamespace(status="failed", error_message="some earlier error")

    mark_source_no_content(_FakeSession(), source)

    assert source.status == "no_content"
    assert source.error_message == NO_CONTENT_MESSAGE
