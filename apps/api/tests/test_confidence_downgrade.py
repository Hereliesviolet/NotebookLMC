"""Confidence handling when citation validation drops everything."""

import pytest

from app.rag.citation_validation import downgrade_confidence_if_unsupported


@pytest.mark.parametrize("confidence", ["medium", "high"])
def test_answer_without_surviving_citations_is_forced_to_low(confidence):
    assert downgrade_confidence_if_unsupported(confidence, 0) == "low"


@pytest.mark.parametrize("confidence", ["low", "medium", "high"])
def test_answer_with_citations_keeps_its_confidence(confidence):
    assert downgrade_confidence_if_unsupported(confidence, 2) == confidence


def test_unknown_confidence_value_falls_back_to_medium():
    assert downgrade_confidence_if_unsupported("certain", 1) == "medium"


def test_unknown_confidence_value_without_citations_is_low():
    assert downgrade_confidence_if_unsupported("certain", 0) == "low"
