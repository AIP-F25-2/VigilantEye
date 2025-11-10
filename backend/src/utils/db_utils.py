import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Iterable, Tuple

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DatabaseError, OperationalError
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from src.app import db

logger = logging.getLogger(__name__)


def check_db_connection(db_session: Session) -> Tuple[bool, str]:
    """Execute a lightweight query to verify database connectivity."""
    try:
        db_session.execute(text("SELECT 1"))
        return True, "Connected"
    except Exception as exc:
        logger.error("Database connectivity check failed: %s", exc, exc_info=True)
        return False, str(exc)


def retry_on_db_error(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator providing retry logic with exponential backoff for transient DB errors."""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            sleep = delay
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DatabaseError) as exc:
                    attempt += 1
                    logger.warning(
                        "Database operation failed (attempt %s/%s): %s",
                        attempt,
                        max_attempts,
                        exc,
                        exc_info=True,
                    )
                    if attempt >= max_attempts:
                        raise
                    time.sleep(sleep)
                    sleep *= backoff

        return wrapper

    return decorator


@contextmanager
def get_db_session():
    """Yield a scoped database session, ensuring proper cleanup."""
    SessionLocal = scoped_session(sessionmaker(bind=db.engine))
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Rolling back database session due to error")
        raise
    finally:
        SessionLocal.remove()


def batch_delete(model_class, filter_condition, batch_size: int = 1000) -> int:
    """Delete rows in batches to avoid long-running transactions."""
    deleted_total = 0
    with get_db_session() as session:
        query = session.query(model_class).filter(filter_condition)
        while True:
            batch = query.limit(batch_size).all()
            if not batch:
                break
            for row in batch:
                session.delete(row)
            session.commit()
            deleted = len(batch)
            deleted_total += deleted
            logger.debug("Deleted %s records from %s", deleted, model_class.__name__)
    return deleted_total


def get_pool_stats(db_engine: Engine | None = None) -> dict[str, Any]:
    """Return statistics about the connection pool."""
    engine = db_engine or db.engine
    pool = engine.pool
    stats = {
        "pool_size": getattr(pool, "size", lambda: None)(),
        "checked_in": getattr(pool, "checkedin", lambda: None)(),
        "checked_out": getattr(pool, "checkedout", lambda: None)(),
        "overflow": getattr(pool, "overflow", lambda: None)(),
    }
    return stats


def log_slow_queries(threshold_ms: int = 1000):
    """Decorator to log queries exceeding the supplied threshold."""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration_ms = (time.perf_counter() - start) * 1000
            if duration_ms > threshold_ms:
                statement = kwargs.get("statement") or kwargs.get("query")
                params = kwargs.get("params") or kwargs.get("parameters")
                logger.warning(
                    "Slow database operation detected: %s took %.2f ms; statement=%s; params=%s",
                    func.__name__,
                    duration_ms,
                    getattr(statement, "text", statement),
                    params,
                )
            return result

        return wrapper

    return decorator


def execute_in_transaction(db_session: Session, operations: Iterable[Callable[[Session], Any]]) -> tuple[bool, Any]:
    """Execute multiple operations within a single transaction."""
    try:
        results = []
        for op in operations:
            results.append(op(db_session))
        db_session.commit()
        return True, results
    except Exception as exc:
        db_session.rollback()
        logger.error("Transaction failed, rolled back: %s", exc, exc_info=True)
        return False, exc


def init_db(app) -> None:
    """Initialise database structures within application context."""
    with app.app_context():
        env = app.config.get("ENV", "production").lower()
        alembic_cfg = Config(os.path.join(app.root_path, "..", "alembic.ini"))
        alembic_cfg.set_main_option("script_location", os.path.join(app.root_path, "..", "migrations"))
        alembic_cfg.set_main_option("sqlalchemy.url", app.config["SQLALCHEMY_DATABASE_URI"])

        logger.info("Applying Alembic migrations for %s environment", env)
        command.upgrade(alembic_cfg, "head")

        from src.config.constants import UserRole
        from src.models import Camera, User

        if not User.query.filter_by(username="admin").first():
            logger.info("Seeding default admin user")
            admin = User(
                username="admin",
                email="admin@vigilanteye.local",
                role=UserRole.ADMIN.value,
                is_active=True,
            )
            admin.set_password("admin123")
            db.session.add(admin)

        if not Camera.query.filter_by(name="Default Camera").first():
            logger.info("Seeding default camera")
            camera = Camera(name="Default Camera", status="active")
            camera.last_active = datetime.utcnow()
            db.session.add(camera)

        db.session.commit()
        logger.info("Database initialisation complete")

