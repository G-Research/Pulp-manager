"""Generates prometheus stats from data in the pulp manager DB and servers them over HTTP
"""
from collections import defaultdict
import time
from datetime import datetime, timedelta
import re
import docker
import requests

from prometheus_client.core import GaugeMetricFamily, REGISTRY
from prometheus_client import start_http_server

from pulp_manager.app.database import session
from pulp_manager.app.repositories import PulpServerRepository, PulpServerRepoRepository, \
TaskRepository


class PulpManagerCollector:
    """Class that collects data from pulp manager database and exposes as prometheus metrics
    """

    def __init__(self):
        try:
            self.docker_client = docker.from_env()  # Initialize Docker client
        except: # pylint: disable=bare-except
            pass

    #pylint:disable=too-many-locals, too-many-branches, too-many-statements
    def collect(self):
        """Carries out the collection of data and turns it into metrics
        """

        try:
            db = session()
            pulp_server_crud = PulpServerRepository(db)
            pulp_server_repo_crud = PulpServerRepoRepository(db)

            one_day_ago = datetime.now() - timedelta(days=1)
            task_crud = TaskRepository(db)
            now = datetime.utcnow()

            pulp_servers = pulp_server_crud.filter()
            pulp_server_repos = pulp_server_repo_crud.filter(eager=["pulp_server", "repo"])
            tasks = task_crud.filter(**{"date_created__ge": one_day_ago})

            containers_status_metric = GaugeMetricFamily(
            "docker_container_status",
            "Status of Docker containers (1 for running, 0 for stopped)",
            labels=["container_name"]
            )

            # Pulling metrics for all docker containers.  May need to list them instead later.
            try:
                for container in self.docker_client.containers.list(all=True):
                    status = 1 if container.status == "running" else 0
                    containers_status_metric.add_metric(
                        [container.name], status)
            except: # pylint: disable=bare-except
                containers_status_metric.add_metric(["Docker failed", 0], 0)

            pulp_server_gague_metric = GaugeMetricFamily(
                "pulp_manager_pulp_server_repo_sync_health_rollup",
                "Pulp Server repo sync health rollup",
                labels=["pulp_server_name", "repo_sync_health_rollup"]
            )

            pulp_server_health_rollup_run_metric = GaugeMetricFamily(
                "pulp_manager_pulp_server_repo_sync_health_rollup_last_run_seconds",
                "Last time the pulp server repo sync health rollup was last run. -1 means never",
                labels=["pulp_server_name"]
            )

            pulp_server_repo_gague_metric = GaugeMetricFamily(
                "pulp_manager_pulp_server_repo_sync_health",
                "Pulp Serve repo sync health for individual repo",
                labels=["pulp_server_name", "repo_name", "repo_sync_health", "has_remote"]
            )

            pulp_server_repo_sync_run_metric = GaugeMetricFamily(
                "pulp_manager_pulp_server_repo_sync_health_last_run_seconds",
                "Last time the pulp server repo sync health check was last run. -1 means never",
                labels=["pulp_server_name", "repo_name"]
            )
            # Queued State
            tasks_queued = GaugeMetricFamily(
                "pulp_manager_pulp_server_tasks_in_queued_state",
                "Pulp Server count of all tasks created this week that are currently queued",
                labels=["pulp_server_name"]
            )

            # Running State
            tasks_running = GaugeMetricFamily(
                "pulp_manager_pulp_server_tasks_in_running_state",
                "Pulp Server count of all tasks created this week that are currently running",
                labels=["pulp_server_name"]
            )

            # Completed State
            tasks_completed = GaugeMetricFamily(
                "pulp_manager_pulp_server_tasks_in_completed_state",
                "Pulp Server count of all tasks created this week that have completed",
                labels=["pulp_server_name"]
            )

            # Failed State
            tasks_failed = GaugeMetricFamily(
                "pulp_manager_pulp_server_tasks_in_failed_state",
                "Pulp Server count of all tasks created this week that have failed",
                labels=["pulp_server_name"]
            )

            # Canceled State
            tasks_canceled = GaugeMetricFamily(
                "pulp_manager_pulp_server_tasks_in_canceled_state",
                "Pulp Server count of all tasks created this week that were canceled",
                labels=["pulp_server_name"]
            )

            # Failed to Start State
            tasks_failed_to_start = GaugeMetricFamily(
                "pulp_manager_pulp_server_tasks_in_failed_to_start_state",
                "Pulp Server count of all tasks created this week that failed to start",
                labels=["pulp_server_name"]
            )

            # Skipped State
            tasks_skipped = GaugeMetricFamily(
                "pulp_manager_pulp_server_tasks_in_skipped_state",
                "Pulp Server count of all tasks created this week that were skipped",
                labels=["pulp_server_name"]
            )

            # Checking if pulp servers can access their databases
            database_connection_metric = GaugeMetricFamily(
                "pulp_manager_pulp_server_database_connection",
                "Status of Pulp server database connectivity",
                labels=["pulp_server_name"]
            )

            # Checking if pulp servers can access their redis instances
            redis_connection_metric = GaugeMetricFamily(
                "pulp_manager_pulp_server_redis_connection",
                "Status of Pulp server redis connectivity",
                labels=["pulp_server_name"]
            )

            # Automatically create a nested dictionary when keys don't exist
            # and start first value at 0
            task_counts = defaultdict(lambda: defaultdict(lambda: 0))

            for task in tasks:

                hostname_pattern = r"\b[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
                task_pulp_server = re.search(hostname_pattern, task.name)

                if not task_pulp_server:
                    continue

                server_name = task_pulp_server.group(0)
                task_state_id = task.state_id
                task_counts[server_name][task_state_id] += 1

            for server, states in task_counts.items():
                for state_id, count in states.items():
                    label = [server]
                    if state_id == 1:
                        tasks_queued.add_metric(label, count)
                    elif state_id == 2:
                        tasks_running.add_metric(label, count)
                    elif state_id == 3:
                        tasks_completed.add_metric(label, count)
                    elif state_id == 4:
                        tasks_failed.add_metric(label, count)
                    elif state_id == 5:
                        tasks_canceled.add_metric(label, count)
                    elif state_id == 6:
                        tasks_failed_to_start.add_metric(label, count)
                    elif state_id == 7:
                        tasks_skipped.add_metric(label, count)

            for pulp_server in pulp_servers:

                repo_sync_health_rollup = pulp_server.repo_sync_health_rollup
                repo_sync_health_rollup_date = pulp_server.repo_sync_health_rollup_date
                repo_sync_health_rollup_last_run = -1

                if repo_sync_health_rollup is None:
                    repo_sync_health_rollup = "None"

                if repo_sync_health_rollup_date:
                    repo_sync_health_rollup_last_run = (now - repo_sync_health_rollup_date).seconds

                pulp_server_gague_metric.add_metric(
                    [
                        pulp_server.name,
                        repo_sync_health_rollup,
                    ],
                    1
                )

                pulp_server_health_rollup_run_metric.add_metric(
                    [pulp_server.name], repo_sync_health_rollup_last_run
                )

            for pulp_server_repo in pulp_server_repos:
                repo_sync_health = pulp_server_repo.repo_sync_health
                repo_sync_health_date = pulp_server_repo.repo_sync_health_date
                repo_sync_health_last_run = -1

                if repo_sync_health is None:
                    repo_sync_health = "None"

                if repo_sync_health_date:
                    repo_sync_health_last_run = (now - repo_sync_health_date).seconds

                pulp_server_repo_gague_metric.add_metric(
                    [
                        pulp_server_repo.pulp_server.name,
                        pulp_server_repo.repo.name,
                        repo_sync_health,
                        "1" if pulp_server_repo.remote_href else "0"
                    ],
                    1
                )

                pulp_server_repo_sync_run_metric.add_metric(
                    [pulp_server_repo.pulp_server.name, pulp_server_repo.repo.name],
                    repo_sync_health_last_run
                )

            for pulp_server in pulp_servers:
                api_endpoint = 'https://' + pulp_server.name + '/pulp/api/v3/status/'

                try:
                    response = requests.get(api_endpoint, timeout=3)
                    # Parse the JSON response
                    data = response.json()

                    # Extract 'database_connection' and 'redis_connection'
                    database_connection = int(data['database_connection']['connected'])
                    redis_connection = int(data['database_connection']['connected'])

                    # Print the extracted values
                    database_connection_metric.add_metric([pulp_server.name], database_connection)
                    redis_connection_metric.add_metric([pulp_server.name], redis_connection)

                except: # pylint: disable=bare-except
                    # if API doesnt respond avoid breaking the rest of the metrics
                    pass

            yield database_connection_metric
            yield redis_connection_metric
            yield containers_status_metric
            yield pulp_server_gague_metric
            yield pulp_server_health_rollup_run_metric
            yield pulp_server_repo_gague_metric
            yield pulp_server_repo_sync_run_metric
            yield tasks_queued
            yield tasks_running
            yield tasks_completed
            yield tasks_failed
            yield tasks_canceled
            yield tasks_failed_to_start
            yield tasks_skipped

        finally:
            db.close()


if __name__ == '__main__':
    REGISTRY.register(PulpManagerCollector())
    start_http_server(9300)
    while True:
        time.sleep(1)
