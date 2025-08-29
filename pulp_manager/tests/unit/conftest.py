"""Setup shared functions for tests
"""
import alembic
import os
import pathlib
import pytest
import fakeredis
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from rq import Queue
from rq_scheduler import Scheduler

from pulp3_bindings.pulp3 import Pulp3Client
from pulp_manager.app.database import DB_URL
from pulp_manager.tests.sample_data_setup import sample_data_insert


# Test jobs to queue into fake redis
def success_job():
    return True


def fail_job():
    raise Exception("oh no!")


# Apply migrations at beginning and end of testing session
# if want to apply for each test then remove the scope parameter
@pytest.fixture(scope="module", autouse=True)
def apply_migrations():
    """Applies database migrations
    """

    # if get the directory for the path of the file that was run
    alembic_path = os.path.join(str(pathlib.Path().resolve()), "alembic.ini")
    # Set in testing mode incase any extra actions are to be carried out
    os.environ["TESTING"] = "1"
    config = Config(alembic_path)

    # Not using asyncio here
    sqlalchemy_url = f"mysql+pymysql://{DB_URL}"
    config.set_main_option("sqlalchemy.url", sqlalchemy_url)

    alembic.command.upgrade(config, "head")
    sample_data_insert()
    yield

    # Downgrade the DB at the end of the tests
    alembic.command.downgrade(config, "base")


def get_fake_redis() -> fakeredis:
    """Populates a fake redis with some sample data so that it can be used
    as an override in the FastAPI Test app
    """

    fake_redis =  fakeredis.FakeStrictRedis()

    # Generate some success and fail jobs
    # is_async=False instructs rq to instantly perform the job in the same thread instead of
    # dispatching it to the workers
    queue = Queue(name="default", is_async=False, connection=fake_redis)
    scheduler = Scheduler(queue=queue, connection=fake_redis)

    job = queue.enqueue(success_job)
    job = queue.enqueue(success_job)
    job = queue.enqueue(fail_job)

    # This menas a worker will be required to proces the job which will then leave it
    # in a scheduled state
    queue = Queue(name="default", is_async=True, connection=fake_redis)
    scheduler.cron(
        "0 0 * * *",
        func=success_job,
        queue_name="default"
    )

    return fake_redis


@pytest.fixture
def fake_redis() -> fakeredis:
    """Fixture for getting fakeredis
    """

    return get_fake_redis()


@pytest.fixture
def app(apply_migrations: None) -> FastAPI:
    """Creates a new application for testing
    """

    from pulp_manager.app.main import get_application
    from pulp_manager.app.redis_connection import get_redis_connection
    app = get_application()
    app.dependency_overrides[get_redis_connection] = get_fake_redis
    return app

@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Returns a test client that can be used for carrying out HTTP tests
    """

    return TestClient(app)