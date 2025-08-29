"""Runs an instance of a pulp manager worker
"""

import socket
from redis import Redis
from rq import Worker
from pulp_manager.app.config import CONFIG

# Currently only have a default queue
worker = Worker(
    ['default'],
    connection=Redis(
        host=CONFIG['redis']['host'],
        port=int(CONFIG['redis']['port']),
        db=int(CONFIG['redis']['db'])
    ),
    name=socket.gethostname()
)
worker.work()
