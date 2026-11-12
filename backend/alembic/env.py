from alembic import context
from sqlalchemy import create_engine, text

from app.config import get_settings
from app.database.base import Base
import app.models  # noqa: F401  (registers all tables on Base.metadata)

target_metadata = Base.metadata
url = get_settings().database_url


def run_migrations_online() -> None:
    engine = create_engine(url)
    with engine.connect() as conn:
        # pgvector must exist before any vector column is created.
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
        context.configure(connection=conn, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    run_migrations_online()
