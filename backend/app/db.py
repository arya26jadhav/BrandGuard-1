
from collections.abc import Generator
from contextlib import contextmanager

from fastapi import Request
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import get_settings


def create_pool() -> ConnectionPool:
    settings = get_settings()

    return ConnectionPool(
        conninfo=settings.database_url,
        min_size=0,
        max_size=5,
        timeout=10,
        kwargs={"row_factory": dict_row},
        check=ConnectionPool.check_connection,
        open=False,
    )


@contextmanager
def connection_context(
    pool: ConnectionPool,
) -> Generator[Connection, None, None]:
    with pool.connection() as conn:
        yield conn


def get_conn(request: Request) -> Generator[Connection, None, None]:
    pool: ConnectionPool = request.app.state.db_pool

    with pool.connection() as conn:
        yield conn
