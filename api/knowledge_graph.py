"""Compatibility shim: default production store lives in sqlite_knowledge_store."""

from pathlib import Path

from sqlite_knowledge_store import SqliteKnowledgeStore

DB_PATH = Path(__file__).parent / "db" / "groundwork.db"

KnowledgeGraph = SqliteKnowledgeStore

__all__ = ["DB_PATH", "KnowledgeGraph", "SqliteKnowledgeStore"]
