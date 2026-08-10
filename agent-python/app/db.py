import os
from contextlib import contextmanager
from threading import Lock
from typing import Generator

from psycopg2.extensions import connection
from psycopg2.pool import ThreadedConnectionPool


class Database:
    """Small, lazily initialized connection pool backed by DATABASE_URL."""

    def __init__(self) -> None:
        self._pool: ThreadedConnectionPool | None = None
        self._lock = Lock()

    def _get_pool(self) -> ThreadedConnectionPool:
        if self._pool is None:
            with self._lock:
                if self._pool is None:
                    database_url = os.getenv("DATABASE_URL")
                    if not database_url:
                        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다.")
                    self._pool = ThreadedConnectionPool(
                        minconn=1,
                        maxconn=int(os.getenv("DB_POOL_MAX_SIZE", "5")),
                        dsn=database_url,
                        connect_timeout=5,
                        application_name="deepsight-agent-python",
                    )
        return self._pool

    @contextmanager
    def connection(self) -> Generator[connection, None, None]:
        pool = self._get_pool()
        conn = pool.getconn()
        try:
            conn.set_session(readonly=True, autocommit=False)
            yield conn
            conn.rollback()
        except Exception:
            conn.rollback()
            raise
        finally:
            pool.putconn(conn)

    def ping(self) -> None:
        with self.connection() as conn, conn.cursor() as cursor:
            cursor.execute("select 1")
            cursor.fetchone()

    def close(self) -> None:
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None


db = Database()
