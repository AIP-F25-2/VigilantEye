import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv

from src.app import create_app, db
from src.models import *  # noqa: F401,F403

load_dotenv()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

app = create_app()
override_url = os.getenv("ALEMBIC_SQLALCHEMY_URL")
if override_url:
    app.config["SQLALCHEMY_DATABASE_URI"] = override_url
database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
config.set_main_option("sqlalchemy.url", database_uri)

target_metadata = db.Model.metadata
x_args = context.get_x_argument(as_dictionary=True)
force_offline = str(x_args.get("offline", "false")).lower() in {"1", "true", "yes"}


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    with app.app_context():
        connectable = db.engine

        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
            )

            with context.begin_transaction():
                context.run_migrations()


if force_offline or context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

