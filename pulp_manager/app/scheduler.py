#!/usr/bin/env python
"""This script is copied from
https://github.com/rq/rq-scheduler/blob/master/rq_scheduler/scripts/rqscheduler.py
and is altered slightly for user by pulp manager
"""

import argparse
import sys
import os

from redis import Redis
from rq_scheduler.scheduler import Scheduler

from rq_scheduler.utils import setup_loghandlers

from pulp_manager.app.config import CONFIG


def main():
    """Entry point to starting the scheduler
    """

    parser = argparse.ArgumentParser(description='Runs RQ scheduler')
    parser.add_argument('-b', '--burst', action='store_true', default=False,
            help='Run in burst mode (quit after all work is done)')
    parser.add_argument('--verbose', '-v', action='store_true', default=False,
            help='Show more output')
    parser.add_argument('--quiet', action='store_true', default=False, help='Show less output')
    parser.add_argument('-i', '--interval', default=60.0, type=float
            , help="How often the scheduler checks for new jobs to add to the \
            queue (in seconds, can be floating-point for more precision).")
    parser.add_argument('--path', default='.', help='Specify the import path.')
    parser.add_argument('--pid', help='A filename to use for the PID file.', metavar='FILE')
    parser.add_argument('-j', '--job-class', help='Custom RQ Job class')
    parser.add_argument('-q', '--queue-class', help='Custom RQ Queue class')

    args = parser.parse_args()

    if args.path:
        sys.path = args.path.split(':') + sys.path

    # pylint: disable=unspecified-encoding
    if args.pid:
        pid = str(os.getpid())
        filename = args.pid
        with open(filename, 'w') as f:
            f.write(pid)

    connection = Redis(
        host=CONFIG['redis']['host'],
        port=int(CONFIG['redis']['port']),
        db=int(CONFIG['redis']['db'])
    )

    if args.verbose:
        level = 'DEBUG'
    elif args.quiet:
        level = 'WARNING'
    else:
        level = 'INFO'
    setup_loghandlers(level)

    scheduler = Scheduler(connection=connection,
                          interval=args.interval,
                          job_class=args.job_class,
                          queue_class=args.queue_class)
    scheduler.run(burst=args.burst)

if __name__ == '__main__':
    main()
