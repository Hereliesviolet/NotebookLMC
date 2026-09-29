from app.rag.retrieval import RetrievedChunk, apply_score_heuristic


def _chunk(chunk_id: str, source_id: str, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        score=score,
        source_id=source_id,
        document_name=f"{source_id}.txt",
        page_start=None,
        page_end=None,
        heading=None,
        chunk_type="text",
    )


def _dominant_source_scenario() -> list[RetrievedChunk]:
    dominant = [_chunk(f"dom-{i}", "source-dominant", score=0.9 - i * 0.001) for i in range(50)]
    minor_sources = []
    for source_id in ("source-a", "source-b", "source-c"):
        minor_sources += [
            _chunk(f"{source_id}-0", source_id, score=0.3),
            _chunk(f"{source_id}-1", source_id, score=0.25),
        ]
    return dominant + minor_sources


def test_apply_score_heuristic_guarantees_at_least_one_chunk_per_source():
    chunks = _dominant_source_scenario()

    result = apply_score_heuristic(chunks, top_k=10, max_chunks_per_source=4)

    represented_sources = {c.source_id for c in result}
    assert represented_sources == {"source-dominant", "source-a", "source-b", "source-c"}
    assert len(result) == 10


def test_apply_score_heuristic_respects_top_k():
    chunks = _dominant_source_scenario()

    result = apply_score_heuristic(chunks, top_k=5, max_chunks_per_source=4)

    assert len(result) == 5
    assert {c.source_id for c in result} == {"source-dominant", "source-a", "source-b", "source-c"}


def test_apply_score_heuristic_fills_remaining_slots_by_score_after_diversity_guarantee():
    chunks = _dominant_source_scenario()

    result = apply_score_heuristic(chunks, top_k=10, max_chunks_per_source=4)

    per_source_count = {}
    for chunk in result:
        per_source_count[chunk.source_id] = per_source_count.get(chunk.source_id, 0) + 1
    assert per_source_count["source-dominant"] == 4
    assert per_source_count["source-a"] == 2
    assert per_source_count["source-b"] == 2
    assert per_source_count["source-c"] == 2


def test_apply_score_heuristic_single_source_behaves_like_plain_top_k():
    chunks = [_chunk(f"c{i}", "only-source", score=float(100 - i)) for i in range(20)]

    result = apply_score_heuristic(chunks, top_k=10, max_chunks_per_source=4)

    assert [c.chunk_id for c in result] == [f"c{i}" for i in range(10)]


def test_apply_score_heuristic_no_chunks_returns_empty():
    assert apply_score_heuristic([], top_k=10, max_chunks_per_source=4) == []


def test_apply_score_heuristic_result_sorted_by_score_descending():
    chunks = _dominant_source_scenario()

    result = apply_score_heuristic(chunks, top_k=10, max_chunks_per_source=4)

    scores = [c.score for c in result]
    assert scores == sorted(scores, reverse=True)
