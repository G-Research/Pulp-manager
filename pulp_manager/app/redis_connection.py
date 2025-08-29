"""Setups up a connection to redis which can be used by FastAPI.
Allows to override dependencies and then provide a different connection
"""
from redis import Redis
from pulp_manager.app.config import CONFIG


def get_redis_connection():
    """Yields a redis connection and closes it
    """

    try:
        redis_conn = Redis(
            host=CONFIG['redis']['host'],
            port=int(CONFIG['redis']['port']),
            db=int(CONFIG['redis']['db'])
        )
        yield redis_conn
    finally:
        redis_conn.close()
