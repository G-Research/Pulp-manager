"""Tests for the RepoRemover service
"""

import pytest
from mock import patch, MagicMock
from pulp3_bindings.pulp3 import Pulp3Client

from pulp_manager.app.database import session, engine
from pulp_manager.app.models import PulpServer
from pulp_manager.app.services.repo_remover import RepoRemover
from pulp_manager.app.exceptions import  PulpManagerValueError


class TestRepoRemover:
    """Tests the repo remover to ensure it correctly handles repository removal operations
    """

    @patch("pulp_manager.app.services.repo_remover.new_pulp_client")
    def setup_method(self, method, mock_new_pulp_client):
        """Ensure an instance of RepoRemover is available for all tests along with
        some mocked data
        """
        def new_pulp_client(pulp_server: PulpServer):
            return Pulp3Client(pulp_server.name, username=pulp_server.username, password="test")
        
        mock_new_pulp_client.side_effect = new_pulp_client

         # Use a pulp server from the sample data insert
        self.db = session()
        self.repo_remover = RepoRemover(self.db, "pulpserver1.domain.local")

    def teardown_method(self):
        """Ensure db connections are closed
        """

        self.db.close()
        engine.dispose()
    
    @patch("pulp_manager.app.services.reconciler.PulpReconciler.reconcile", autospec=True)
    @patch("pulp_manager.app.services.repo_remover.delete_by_href_monitor")
    def test_remove_repos(self, mock_delete_by_href_monitor,  mock_reconcile):
        """Tests the removal process of repositories in both dry run and actual deletion modes
        """
        
        # There are two repos assigned ot the pulp server
        # named repo1 and repo2 from sample data
        # Test dry run mode
        self.repo_remover.remove_repos(regex_include="repo.*", dry_run=True)
        mock_delete_by_href_monitor.assert_not_called()

        # Test actual deletion mode
        self.repo_remover.remove_repos(regex_include="repo.*", dry_run=False)
        assert mock_delete_by_href_monitor.call_count == 2
        mock_reconcile.assert_called_once()
    
    @patch("pulp_manager.app.services.repo_remover.get_pulp_server_repos")
    def test_no_repos_found_for_removal(self, mock_get_pulp_server_repos):
        """Tests the behavior when no repositories match the given regex
        """
        mock_get_pulp_server_repos.return_value = []
        with pytest.raises(PulpManagerValueError):
            self.repo_remover.remove_repos(regex_include="nonexistent.*")
