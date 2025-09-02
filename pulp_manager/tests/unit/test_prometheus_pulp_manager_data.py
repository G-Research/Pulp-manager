"""Tests that prometheus metrics are successfully generate from
data stored in the DB
"""

from pulp_manager.app.prometheus_pulp_manager_data import PulpManagerCollector


class TestPulpManagerCollector:
    """Tests the pulp manager collector
    """

    def test_collector(self):
        """Tests the collector runs successfully
        """

        collector = PulpManagerCollector()
        collector.collect()
