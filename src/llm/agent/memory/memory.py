import uuid
from pathlib import Path

import chromadb

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DB_PATH = _PROJECT_ROOT / "memory_db"

class MemoryStore:
    def __init__(self) -> None:
        client = chromadb.PersistentClient(path=str(_DB_PATH))
        self._collection = client.get_or_create_collection("messages")

    def store(self, user_name: str, content: str, role: str) -> None:
        self._collection.add(
            documents=[content],
            metadatas=[{"user_name": user_name, "role": role}],
            ids=[str(uuid.uuid4())],
        )

    def query(self, user_name: str, query_text: str, n_results: int = 5) -> list[str]:
        count = self._collection.count()
        if count == 0:
            return []

        results = self._collection.query(
            query_texts=[query_text],
            n_results=min(n_results, count),
            where={"user_name": user_name},
        )
        return results["documents"][0]
