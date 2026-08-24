import hashlib
import math
from pathlib import Path

import tiktoken
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_postgres import PGVector

from .config import Settings, get_settings


class HashEmbeddings(Embeddings):
    """Offline deterministic embeddings; FastEmbed can replace this through the same interface."""

    dimensions = 384

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = text.lower().split()
        for token in tokens:
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:2], "big") % self.dimensions
            vector[index] += -1.0 if digest[2] & 1 else 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def token_chunks(text: str, size: int = 400, overlap: int = 80) -> list[str]:
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    chunks = []
    step = max(1, size - overlap)
    for start in range(0, len(tokens), step):
        part = tokens[start : start + size]
        if not part:
            break
        chunks.append(encoding.decode(part))
        if start + size >= len(tokens):
            break
    return chunks


class KnowledgeBase:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.embeddings = HashEmbeddings()
        self.local_docs = self._load_documents()
        self.store: PGVector | None = None

    def _load_documents(self) -> list[Document]:
        docs: list[Document] = []
        knowledge_dir = Path(__file__).resolve().parents[1] / "knowledge"
        for source in sorted(knowledge_dir.glob("*.md")):
            for index, chunk in enumerate(token_chunks(source.read_text(encoding="utf-8"))):
                docs.append(
                    Document(page_content=chunk, metadata={"source": source.name, "chunk": index})
                )
        return docs

    def initialize(self) -> None:
        self.store = PGVector(
            embeddings=self.embeddings,
            collection_name="website_builder_knowledge",
            connection=self.settings.database_url,
            use_jsonb=True,
            create_extension=True,
        )
        if self.local_docs:
            ids = [f"{doc.metadata['source']}:{doc.metadata['chunk']}" for doc in self.local_docs]
            self.store.add_documents(self.local_docs, ids=ids)

    def retrieve(self, queries: list[str], limit: int = 6) -> list[str]:
        rankings: list[list[Document]] = []
        if self.store is not None:
            for query in queries:
                rankings.append(self.store.similarity_search(query, k=limit))
        else:
            for query in queries:
                terms = set(query.lower().split())
                rankings.append(
                    sorted(
                        self.local_docs,
                        key=lambda doc: len(terms & set(doc.page_content.lower().split())),
                        reverse=True,
                    )[:limit]
                )
        scores: dict[str, float] = {}
        documents: dict[str, str] = {}
        for ranking in rankings:
            for rank, document in enumerate(ranking):
                key = hashlib.sha1(document.page_content.encode()).hexdigest()
                scores[key] = scores.get(key, 0.0) + 1 / (60 + rank + 1)
                documents[key] = document.page_content
        return [documents[key] for key in sorted(scores, key=scores.get, reverse=True)[:limit]]
