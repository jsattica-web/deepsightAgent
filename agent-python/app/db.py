import os
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import ContextManager, Generator

from dotenv import load_dotenv
from psycopg2.extensions import connection
from psycopg2.pool import ThreadedConnectionPool

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)


class Database:
    """PostgreSQL 커넥션 풀을 관리하는 작은 클래스이다."""

    def __init__(self) -> None:
        """DB 풀은 실제 DB 호출이 생길 때 만들기 위해 초기값만 준비한다."""
        self._pool: ThreadedConnectionPool | None = None
        self._lock = Lock()

    def _get_pool(self) -> ThreadedConnectionPool:
        """DATABASE_URL 환경변수를 이용해 PostgreSQL 커넥션 풀을 지연 생성한다."""
        if self._pool is None:
            with self._lock:
                # 여러 요청이 동시에 들어와도 커넥션 풀은 한 번만 생성한다.
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
        """읽기 전용 DB 커넥션을 빌려주고 사용 후 풀에 안전하게 반납한다."""
        pool = self._get_pool()
        conn = pool.getconn()
        try:
            # Tool은 조회 전용으로 사용하므로 실수로 DB를 변경하지 않게 readonly로 둔다.
            conn.set_session(readonly=True, autocommit=False)
            yield conn
            conn.rollback()
        except Exception:
            conn.rollback()
            raise
        finally:
            pool.putconn(conn)

    def ping(self) -> None:
        """간단한 select 쿼리로 DB 연결 가능 여부를 확인한다."""
        with self.connection() as conn, conn.cursor() as cursor:
            cursor.execute("select 1")
            cursor.fetchone()

    def close(self) -> None:
        """애플리케이션 종료 시 열려 있는 모든 DB 커넥션을 닫는다."""
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None


db = Database()


def get_connection() -> ContextManager[connection]:
    """Tool 코드에서 공통으로 사용할 읽기 전용 DB 커넥션 컨텍스트를 반환한다."""

    return db.connection()
