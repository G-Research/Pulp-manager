"""Tests for the task repository
"""
import json
import pytest

from pulp_manager.app.database import session, engine
from pulp_manager.app.models import Task, TaskStage
from pulp_manager.app.repositories import TaskRepository, TaskStageRepository


class TestTaskRepository:
    """Tests the task repository. Carries out inserts updates and deletes to ensure
    that foreign key constraints and cascading deletes work as expected
    """

    def setup_method(self):
        """Setup the db and task repository service for all services
        """

        self.db = session()
        self.task_repository = TaskRepository(self.db)

    def teardown_method(self):
        """Ensure db connections closed
        """

        self.db.close()

    def test_no_filter(self):
        """Tests that when no filtering is applied to the db all task objects are returned.
        Sample data inserts at least two tasks, so want to make sure more than one result is
        returned
        """

        result = self.task_repository.filter()
        assert len(result) > 1
        assert isinstance(result[0], Task)

    def test_filter(self):
        """Tests that when filtering is applied to the query the specific task instance
        is returned
        """

        result = self.task_repository.filter(**{"name": "dummy task 1"})
        assert len(result) == 1
        assert isinstance(result[0], Task)

    def test_count(self):
        """Tests that an int is returned by the count function
        """

        result = self.task_repository.count()
        assert isinstance(result, int)
        assert result > 0

    def test_count_filter(self):
        """Tests that an int is returned by the count filter function
        """

        result = self.task_repository.count_filter(**{"name": "dummy task 1"})
        assert isinstance(result, int)
        assert result == 1

    def test_filter_paged(self):
        """Tests that only the number of requested results is returned
        """

        result = self.task_repository.filter_paged(page_size=1)
        assert len(result) == 1

    def test_filter_page_result(self):
        """Tests that the combined page count and results object is result as expected
        """

        result = self.task_repository.filter_paged_result(page_size=1)
        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["page_size"] == 1
        assert result["total"] > 0

        page_0_task_name = result["items"][0].name

        result = self.task_repository.filter_paged_result(page=2, page_size=1)
        page_1_task_name = result["items"][0].name

        assert page_0_task_name != page_1_task_name

    def test_get_first(self):
        """Tests that a single task is returned when a fitler is used
        """

        result = self.task_repository.first(**{"name": "dummy task 1"})
        assert isinstance(result, Task)

    def test_get_by_id(self):
        """Tests that requesting a task by ID returns the expected result
        """

        # First find a task based on name incase any messing around
        # has been done with a test db that could cause IDs to not be
        # an expected value
        result = self.task_repository.filter(**{"name": "dummy task 1"})
        task_id = result[0].id

        result = self.task_repository.get_by_id(task_id)
        assert isinstance(result, Task)
        assert result.id == task_id

    def test_add(self):
        """Tests that a task instnace is returned when the add method is called
        db is flushed to generated an id and then rolled back
        """

        task = self.task_repository.add(**{
            "name": "test task id",
            "task_type_id": 1,
            "state_id": 1,
            "task_args_str": json.dumps({"arg": 1})
        })
        self.db.flush()

        assert isinstance(task, Task)
        assert task.id is not None
        self.db.rollback()

    def test_bulk_add(self):
        """Tests that adding a list of tasks, returns the new objects
        db is flushed to generate task ids and then rolled back once assertions passed
        """

        tasks = self.task_repository.bulk_add([
            {
                "name": "test task 1",
                "task_type_id": 1,
                "state_id": 1,
                "task_args_str": json.dumps({"arg": 1})
            },
            {
                "name": "test task 2",
                "task_type_id": 1,
                "state_id": 1,
                "task_args_str": json.dumps({"arg": 1})
            },
            {
                "name": "test task 3",
                "task_type_id": 1,
                "state_id": 1,
                "task_args_str": json.dumps({"arg": 1})
            },
        ])
        self.db.flush()
        assert isinstance(tasks, list)

        count = 0
        for task in tasks:
            count += 1
            assert task.id is not None
            assert task.name == f"test task {count}"

    def test_update(self):
        """Tests updating a task is successful. This test works by adding a task
        flushing the db, updating the task, flushing the db again and then retrieving
        the updated task. Once assertions have passed the db is rolled back
        """

        task = self.task_repository.add(**{
            "name": "task to update",
            "task_type_id": 1,
            "state_id": 1,
            "task_args_str": json.dumps({"arg": "1"})
        })
        self.db.flush()

        task_id = task.id

        self.task_repository.update(task, **{"state_id": 2})
        self.db.flush()

        task = self.task_repository.get_by_id(task.id)
        assert task.state_id == 2
        self.db.rollback()

    def test_bulk_update(self):
        """Tests bulk updating of tasks. Test works by creating two tasks to update and flushing
        the db. The bulk update is called and then once assertions have passed the db is rolledback
        """

        tasks_for_update = self.task_repository.bulk_add([
            {
                "name": "task to update 1",
                "task_type_id": 1,
                "state_id": 1,
                "task_args_str": json.dumps({"arg": "1"})
            },
            {
                "name": "task to update 2",
                "task_type_id": 1,
                "state_id": 1,
                "task_args_str": json.dumps({"arg": "1"})
            }
        ])
        self.db.flush()

        update_task_config = []
        for task in tasks_for_update:
            update_task_config.append({"id": task.id, "state_id": 2})

        self.task_repository.bulk_update(update_task_config)
        for t in tasks_for_update:
            task = self.task_repository.get_by_id(t.id)
            assert task.state_id == 2

        self.db.rollback()

    def test_delete(self):
        """Tests removing a task from the db. A task is created and the db flushed.
        The task is then removed from the DB and once all assertions have passed the db
        is rolledback
        """

        task = self.task_repository.add(**{
            "name": "task to delete",
            "task_type_id": 1,
            "state_id": 1,
            "task_args_str": json.dumps({"arg": "1"})
        })
        self.db.flush()

        task_id = task.id

        self.task_repository.delete(task)
        self.db.flush()

        task = self.task_repository.get_by_id(task_id)
        assert task is None
        self.db.rollback()


class TestTaskStageRepository:
    """Tests the task stage repository. Carries out inserts updates and deletes to ensure
    that foreign key constraints and cascading deletes work as expected
    """

    def setup_method(self):
        """Setup the db and task repository service for all services
        """

        self.db = session()
        self.task_stage_repository = TaskStageRepository(self.db)

        # Set up a task id that can be sued for task stages
        task_repository = TaskRepository(self.db)
        task = task_repository.first(**{"name": "dummy task 1"})
        self.parent_task_id = task.id

    def teardown_method(self):
        """Ensure db connections are closed
        """

        self.db.close()

    def test_no_filter(self):
        """Tests that when no filtering is applied to the db all task objects are returned.
        Sample data inserts at least two task stages, so want to make sure more than one result is
        returned
        """

        result = self.task_stage_repository.filter()
        assert len(result) > 1
        assert isinstance(result[0], TaskStage)

    def test_filter(self):
        """Tests that when filtering is applied to the query the specific task stage instance
        is returned
        """

        result = self.task_stage_repository.filter(**{"name": "stage 1"})
        assert len(result) == 1
        assert isinstance(result[0], TaskStage)

    def test_count(self):
        """Tests that an int is returned by the count function
        """

        result = self.task_stage_repository.count()
        assert isinstance(result, int)
        assert result > 0

    def test_count_filter(self):
        """Tests that an int is returned by the count filter function
        """

        result = self.task_stage_repository.count_filter(**{"name": "stage 1"})
        assert isinstance(result, int)
        assert result == 1

    def test_filter_paged(self):
        """Tests that only the number of requested results is returned
        """

        result = self.task_stage_repository.filter_paged(page_size=1)
        assert len(result) == 1

    def test_filter_page_result(self):
        """Tests that the combined page count and results object is result as expected
        """

        result = self.task_stage_repository.filter_paged_result(page_size=1)
        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["page_size"] == 1
        assert result["total"] > 0

        page_0_task_name = result["items"][0].name

        result = self.task_stage_repository.filter_paged_result(page=2, page_size=1)
        page_1_task_name = result["items"][0].name

        assert page_0_task_name != page_1_task_name

    def test_get_first(self):
        """Tests that a single task stage is returned when a fitler is used
        """

        result = self.task_stage_repository.first(**{"name": "stage 1"})
        assert isinstance(result, TaskStage)

    def test_get_by_id(self):
        """Tests that requesting a task stage by ID returns the expected result
        """

        # First find a task based on name incase any messing around
        # has been done with a test db that could cause IDs to not be
        # an expected value
        result = self.task_stage_repository.filter(**{"name": "stage 1"})
        task_id = result[0].id

        result = self.task_stage_repository.get_by_id(task_id)
        assert isinstance(result, TaskStage)
        assert result.id == task_id

    def test_add(self):
        """Tests that a task stage instnace is returned when the add method is called
        db is flushed to generated an id and then rolled back
        """

        task_stage = self.task_stage_repository.add(**{
            "name": "stage 3",
            "task_id": self.parent_task_id
        })
        self.db.flush()

        assert isinstance(task_stage, TaskStage)
        assert task_stage.id is not None
        self.db.rollback()

    def test_bulk_add(self):
        """Tests that adding a list of task stages, returns the new objects
        db is flushed to generate task ids and then rolled back once assertions passed
        """

        task_stages = self.task_stage_repository.bulk_add([
            {
                "name": "test task stage 1",
                "task_id": self.parent_task_id
            },
            {
                "name": "test task stage 2",
                "task_id": self.parent_task_id
            },
            {
                "name": "test task stage 3",
                "task_id": self.parent_task_id
            },
        ])
        self.db.flush()
        assert isinstance(task_stages, list)

        count = 0
        for stage in task_stages:
            count += 1
            assert stage.id is not None
            assert stage.name == f"test task stage {count}"

    def test_update(self):
        """Tests updating a task is successful. This test works by adding a task stage
        flushing the db, updating the task stage, flushing the db again and then retrieving
        the updated task stage. Once assertions have passed the db is rolled back
        """

        task_stage = self.task_stage_repository.add(**{
            "name": "test task stage to update",
            "task_id": self.parent_task_id
        })
        self.db.flush()

        task_stage_id = task_stage.id

        self.task_stage_repository.update(
            task_stage, **{"detail_str": json.dumps({"key": "value"})}
        )
        self.db.flush()

        task_stage = self.task_stage_repository.get_by_id(task_stage.id)
        assert task_stage.detail_str is not None
        self.db.rollback()

    def test_bulk_update(self):
        """Tests bulk updating of task stages. Test works by creating two task stages to update
        and flushing the db. The bulk update is called and then once assertions have passed the
        db is rolledback
        """

        task_stages_for_update = self.task_stage_repository.bulk_add([
            {
                "name": "test task stage to update 1",
                "task_id": self.parent_task_id
            },
            {
                "name": "test task stage to update 2",
                "task_id": self.parent_task_id
            }
        ])
        self.db.flush()

        update_task_stage_config = []
        for stage in task_stages_for_update:
            update_task_stage_config.append({
                "id": stage.id, "detail_str": json.dumps({"key": "value"})
            })

        self.task_stage_repository.bulk_update(update_task_stage_config)
        for s in task_stages_for_update:
            stage = self.task_stage_repository.get_by_id(s.id)
            assert stage.detail_str is not None

        self.db.rollback()

    def test_delete(self):
        """Tests removing a task from the db. A task is created and the db flushed.
        The task is then removed from the DB and once all assertions have passed the db
        is rolledback
        """

        task_stage = self.task_stage_repository.add(**{
            "name": "task stage to delete",
            "task_id": self.parent_task_id
        })
        self.db.flush()

        task_stage_id = task_stage.id

        self.task_stage_repository.delete(task_stage)
        self.db.flush()

        task_stage = self.task_stage_repository.get_by_id(task_stage_id)
        assert task_stage is None
        self.db.rollback()
