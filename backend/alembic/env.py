from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings
from app.core.database import Base
from app.models.user import User
from app.models.photo import Photo, PhotoFile
from app.models.album import Album  # Import all models

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set SQLAlchemy URL from settings
# Escape % characters for ConfigParser (% becomes %%)
db_url = settings.DATABASE_URL.replace('+asyncpg', '').replace('%', '%%')
config.set_main_option('sqlalchemy.url', db_url)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table":
        if hasattr(object, "schema") and object.schema != settings.DB_SCHEMA:
            return False
    elif type_ == "index":
        if hasattr(object, "table") and hasattr(object.table, "schema") and object.table.schema != settings.DB_SCHEMA:
            return False
    elif type_ == "foreign_key_constraint":
        if hasattr(object, "table") and hasattr(object.table, "schema") and object.table.schema != settings.DB_SCHEMA:
            return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=settings.DB_SCHEMA,
        include_schemas=False,
        include_object=include_object
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Create schema if not exists BEFORE configuring context
        # This allows Alembic to create the version table inside that schema
        from sqlalchemy import text
        print(f"DEBUG: Ensuring schema '{settings.DB_SCHEMA}' exists...")
        connection.execution_options(isolation_level="AUTOCOMMIT").execute(
            text(f'CREATE SCHEMA IF NOT EXISTS "{settings.DB_SCHEMA}"')
        )
        # connection.commit() # Not needed with AUTOCOMMIT

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=settings.DB_SCHEMA,
            include_schemas=True,
            include_object=include_object
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
