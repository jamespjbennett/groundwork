import pytest
import httpx
from unittest.mock import patch

from memory_knowledge_store import InMemoryKnowledgeStore
from sqlite_knowledge_store import SqliteKnowledgeStore


@pytest.fixture(params=["memory", "sqlite"])
async def store(request, tmp_path):
    """KnowledgeStore contract fixture — runs every test against both backends."""
    if request.param == "memory":
        s = InMemoryKnowledgeStore()
    else:
        s = SqliteKnowledgeStore(db_path=tmp_path / "test.db")
    await s.init()
    return s


@pytest.fixture
def memory_store():
    return InMemoryKnowledgeStore()


@pytest.fixture
async def api_client():
    """httpx client wired to the FastAPI app with an isolated in-memory store."""
    from main import app

    store = InMemoryKnowledgeStore()
    with patch("main.db", store):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client, store
