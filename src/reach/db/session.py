from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from reach.config import settings


DATABASE_URL = f"sqlite:///{settings.database_path.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_session() -> Session:
    return SessionLocal()


def init_db() -> None:
    from reach.db import identity_models  # noqa: F401
    from reach.db import models  # noqa: F401
    from reach.db import campaign_models  # noqa: F401
    from reach.db import compliance_models  # noqa: F401
    from reach.db import mock_message_models  # noqa: F401
    from reach.db.base import Base

    settings.database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    Base.metadata.create_all(bind=engine)
