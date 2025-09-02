"""Common logger configuration to be used by the app
"""
import json
import logging
import sys
from datetime import datetime
from rq import get_current_job
from pulp_manager.app.middleware import get_request_id

class JSONFormatter(logging.Formatter):
    """Structured logging formatter to specify a standard set of JSON fields
    """

    def format(self, record):
        """Outputs the log record in desired format
        :param record: The log entry to output
        :type record: logging.LogRecord
        :returns: dict
        """

        job = get_current_job()

        obj = {
            'msg': record.getMessage(),
            'ts': datetime.utcfromtimestamp(record.created).isoformat(),
            'module': record.module,
            'func': record.funcName,
            'thread': record.threadName,
            'level': record.levelname,
            'worker_id': job.id if job else None,
            'request_id': get_request_id()
        }

        exception = getattr(record, 'exception', {})
        if exception:
            obj['exception'] = exception

        return json.dumps(obj)


log = logging.getLogger()
log.setLevel(logging.INFO)

json_formatter = JSONFormatter()
json_handler = logging.StreamHandler(sys.stderr)
json_handler.setFormatter(json_formatter)

logging.captureWarnings(True)

log.addHandler(json_handler)
