import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sqlalchemy import inspect

from reach.config import settings
from reach.db.models import Document, KnowledgeBase
from reach.db.session import engine, get_session, init_db


def main():
    print("=" * 70)
    print("NAMMAWEB AI - DATABASE VALIDATION")
    print("=" * 70)

    init_db()

    print(f"Database : {settings.database_path}")

    inspector = inspect(engine)
    tables = sorted(inspector.get_table_names())

    print(f"Tables   : {tables}")

    expected = {"knowledge_bases", "documents"}

    if not expected.issubset(set(tables)):
        raise AssertionError(
            f"Missing tables: {sorted(expected - set(tables))}"
        )

    session = get_session()

    try:
        kb = KnowledgeBase(
            name="Database Smoke Test",
            description="Temporary test record.",
        )

        session.add(kb)
        session.flush()

        document = Document(
            knowledge_base_id=kb.id,
            filename="smoke-test.pdf",
            file_path="documents/smoke-test.pdf",
            page_count=1,
            chunk_count=1,
            status="active",
        )

        session.add(document)
        session.flush()

        assert kb.id is not None
        assert document.id is not None
        assert document.knowledge_base_id == kb.id

        print("KnowledgeBase insert : PASS")
        print("Document insert      : PASS")

        session.rollback()

    finally:
        session.close()

    print()
    print("DATABASE VALIDATION: PASS")


if __name__ == "__main__":
    main()
