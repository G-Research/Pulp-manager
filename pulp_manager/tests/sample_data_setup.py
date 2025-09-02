"""Sets up some sample date in the DB which isn't to be altered
"""

import json
from datetime import datetime
from pulp_manager.app.database import session, engine
from pulp_manager.app.models import (
    Task, TaskStage, Repo, RepoGroup, PulpServer, PulpServerRepoGroup, PulpServerRepo,
    PulpServerRepoTask
)


def sample_data_insert():
    """Inserts sample data into the database
    """

    try:
        db = session()
        task1 = Task(**{
            "name": "dummy task 1",
            "task_type_id": 1,
            "state_id": 1,
            "task_args_str": json.dumps({"arg": 1})
        })
        db.add(task1)

        task2 = Task(**{
            "name": "dummy task 2",
            "task_type_id": 1,
            "state_id": 1,
            "task_args_str": json.dumps({"arg": 2})
        })
        db.add(task2)

        task3 = Task(**{
            "name": "dummy task 3",
            "task_type_id": 1,
            "state_id": 1,
            "task_args_str": json.dumps({"arg": 3})
        })
        db.add(task3)
        db.flush()

        sub_task = Task(**{
            "name": "dummy sub take",
            "parent_task_id": task1.id,
            "task_type_id": 1,
            "state_id": 1,
            "task_args_str": json.dumps({"arg": 2})
        })
        db.add(sub_task)
        db.flush()

        task_stage_1 = TaskStage(**{
            "task_id": task1.id,
            "name": "stage 1"
        })
        task_stage_2 = TaskStage(**{
            "task_id": task1.id,
            "name": "stage 2"
        })

        db.add(task_stage_1)
        db.add(task_stage_2)
        db.flush()

        repo1 = Repo(**{
            "name": "repo1",
            "repo_type": "rpm"
        })
        repo2 = Repo(**{
            "name": "repo2",
            "repo_type": "deb"
        })

        db.add(repo1)
        db.add(repo2)
        db.flush()

        repo_group_1 = RepoGroup(**{
            "name": "repo group 1",
            "regex_include": "test-repo"
        })
        repo_group_2 = RepoGroup(**{
            "name": "repo group 2",
            "regex_exclude": "exclude-me"
        })
        db.add(repo_group_1)
        db.add(repo_group_2)
        db.flush()

        pulp_server_1 = PulpServer(**{
            "name": "pulpserver1.domain.local",
            "username": "user1",
            "vault_service_account_mount": "service-accounts",
            "repo_sync_health_rollup": "green"
        })
        pulp_server_2 = PulpServer(**{
            "name": "pulpserver2.domain.local",
            "username": "user1",
            "vault_service_account_mount": "service-accounts",
            "repo_sync_health_rollup": "red"
        })
        pulp_server_3 = PulpServer(**{
            "name": "pulpserver3.domain.local",
            "username": "user1",
            "vault_service_account_mount": "service-accounts",
            "repo_sync_health_rollup": "red"
        })
        db.add(pulp_server_1)
        db.add(pulp_server_2)
        db.add(pulp_server_3)
        db.flush()

        pulp_server1_repo_group_1 = PulpServerRepoGroup(**{
            "pulp_server_id": pulp_server_1.id,
            "repo_group_id": repo_group_1.id,
            "schedule": "0 0 * * *",
            "max_concurrent_syncs": "2",
            "max_runtime": "2h"
        })
        pulp_server1_repo_group_2 = PulpServerRepoGroup(**{
            "pulp_server_id": pulp_server_1.id,
            "repo_group_id": repo_group_2.id,
            "schedule": "0 0 * * *",
            "max_concurrent_syncs": "1",
            "max_runtime": "2h"
        })

        pulp_server2_repo_group_1 = PulpServerRepoGroup(**{
            "pulp_server_id": pulp_server_2.id,
            "repo_group_id": repo_group_1.id,
            "schedule": "0 0 * * *",
            "max_concurrent_syncs": "2",
            "max_runtime": "2h"
        })
        pulp_server2_repo_group_2 = PulpServerRepoGroup(**{
            "pulp_server_id": pulp_server_2.id,
            "repo_group_id": repo_group_2.id,
            "schedule": "0 0 * * *",
            "max_concurrent_syncs": "1",
            "max_runtime": "2h"
        })


        db.add(pulp_server1_repo_group_1)
        db.add(pulp_server1_repo_group_2)
        db.add(pulp_server2_repo_group_1)
        db.add(pulp_server2_repo_group_2)
        db.flush()

        pulp_server_repo_1 = PulpServerRepo(**{
            "pulp_server_id": pulp_server_1.id,
            "repo_id": repo1.id,
            "repo_href": "/pulp/api/v3/repositories/rpm/rpm/abc",
            "repo_sync_health": "green",
            "repo_sync_health_date": datetime.utcnow()
        })
        pulp_server_repo_2 = PulpServerRepo(**{
            "pulp_server_id": pulp_server_1.id,
            "repo_id": repo2.id,
            "repo_href": "/pulp/api/v3/repositories/deb/apt/def",
            "repo_sync_health": "amber",
            "repo_sync_health_date": datetime.utcnow()
        })
        db.add(pulp_server_repo_1)
        db.add(pulp_server_repo_2)
        db.flush()

        pulp_server1_repo_task_1 = PulpServerRepoTask(**{
            "pulp_server_repo_id": pulp_server_repo_1.id,
            "task_id": task1.id
        })
        pulp_server1_repo_task_2 = PulpServerRepoTask(**{
            "pulp_server_repo_id": pulp_server_repo_2.id,
            "task_id": task2.id
        })
        db.add(pulp_server1_repo_task_1)
        db.add(pulp_server1_repo_task_2)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    sample_data_insert()
