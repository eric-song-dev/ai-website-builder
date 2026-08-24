from backend.app.rag import HashEmbeddings, KnowledgeBase, token_chunks


def test_token_chunking_has_overlap():
    text = " ".join(f"word-{index}" for index in range(1200))
    chunks = token_chunks(text, size=100, overlap=20)
    assert len(chunks) > 3
    assert set(chunks[0].split()) & set(chunks[1].split())


def test_hash_embeddings_are_stable_and_normalized():
    model = HashEmbeddings()
    first = model.embed_query("responsive accessible navigation")
    second = model.embed_query("responsive accessible navigation")
    assert first == second
    assert abs(sum(value * value for value in first) - 1) < 1e-6


def test_local_rrf_retrieval_without_database():
    kb = KnowledgeBase()
    results = kb.retrieve(["accessible keyboard focus", "wcag labels"], limit=2)
    assert results
    assert any("focus" in result.lower() or "label" in result.lower() for result in results)
