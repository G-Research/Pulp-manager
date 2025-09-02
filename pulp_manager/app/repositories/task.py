"""repository for task
"""

from pulp_manager.app.models import TaskStage, Task
from pulp_manager.app.repositories.table_repository import TableRepository


class TaskStageRepository(TableRepository):
    """Repository for interacting with TaskStage entities
    """

    __model__ = TaskStage

    def _get_base_filter_join_query(self, eager_load: bool):
        """Returns the query that contains all realted tables joined for querying

        :param eager_load: eagerly load all the joined table
        :type eager_load: bool
        """

        raise NotImplementedError


class TaskRepository(TableRepository):
    """Repository for interacting with task entities
    """

    __model__ = Task
    __field_remap__ = {
        "state": Task.state_id,
        "task_type": Task.task_type_id
    }

    def _get_base_filter_join_query(self, eager_load: bool):
        """Returns the query that contains all realted tables joined for querying

        :param eager_load: eagerly load all the joined table
        :type eager_load: bool
        """

        raise NotImplementedError
