import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.app import create_app, db  # noqa: E402
from src.utils.db_utils import init_db  # noqa: E402


def check_mysql(app) -> tuple[bool, str]:
    try:
        with app.app_context():
            db.session.execute(text("SELECT 1"))
        return True, "Connected to MySQL"
    except SQLAlchemyError as exc:
        return False, f"MySQL connection failed: {exc}"


def check_redis() -> tuple[bool, str]:
    try:
        import redis  # type: ignore

        from src.config import settings  # noqa: WPS433

        redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        client = redis.Redis.from_url(redis_url)
        client.ping()
        return True, f"Connected to Redis at {redis_url}"
    except ImportError:
        return False, "Redis library not installed"
    except Exception as exc:  # noqa: W0703
        return False, f"Redis connection failed: {exc}"


def check_chromadb() -> tuple[bool, str]:
    try:
        import requests  # type: ignore

        from src.config import settings  # noqa: WPS433

        chroma_url = getattr(settings, "CHROMADB_URL", "http://localhost:8000")
        response = requests.get(chroma_url, timeout=5)
        if response.ok:
            return True, f"Connected to ChromaDB at {chroma_url}"
        return False, f"ChromaDB responded with status {response.status_code}"
    except ImportError:
        return False, "Requests library not installed"
    except Exception as exc:  # noqa: W0703
        return False, f"ChromaDB connection failed: {exc}"


def main() -> None:
    app = create_app()

    mysql_ok, mysql_msg = check_mysql(app)
    redis_ok, redis_msg = check_redis()
    chroma_ok, chroma_msg = check_chromadb()

    print(f"[{'OK' if mysql_ok else 'FAIL'}] {mysql_msg}")
    print(f"[{'OK' if redis_ok else 'FAIL'}] {redis_msg}")
    print(f"[{'OK' if chroma_ok else 'FAIL'}] {chroma_msg}")

    init_db(app)
    print("[DONE] Database initialisation complete (migrations applied)")
    print("\nNext steps:")
    print("1. (Optional) Verify migrations: alembic upgrade head")
    print("2. Start the application server: python -m flask run")


if __name__ == "__main__":
    main()

