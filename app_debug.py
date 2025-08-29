import os
from pulp_manager.app.database import session
from pulp_manager.app.services import PulpConfigParser, PulpReconciler, RepoSyncher, PulpManager, Snapshotter, RepoConfigRegister

try:
    db = session()
    #reconciler = PulpReconciler(db, "pulp3mast1.example.com")
    #reconciler.reconcile()
    #repo_syncher = RepoSyncher(db)
    #repo_syncher.sync_repos(
    #    "pulp3slav1.example.com",
    #    2,
    #    regex_include="^mdi-test-2-",
    #    source_pulp_server_name="pulp3mast1.example.com"
    #)
#    snapshotter = Snapshotter(db)
#    snapshotter.snapshot_repos("pulp3mast1.example.com", "mdi-test-3", 4, regex_include="^ext-focal-docker-ce$", allow_snapshot_reuse=True)

    #snapshotter = Snapshotter(db, "pulp3mast1.example.com")
    #snapshotter.snapshot_repos("mdi-test-8", 2, "^ext-el7-hpe-mcp|^ext-focal-hashicorp")

    #repo_syncher = RepoSyncher(db, "pulp3slav1.example.com")
    #repo_syncher.sync_repos(
    #    2,
    #    regex_include="mdi-test-8",
    #    source_pulp_server_name="pulp3mast1.example.com"
    #)

    repo_config_register = RepoConfigRegister(db, "repo.example.com")
    repo_config_register.create_repos_from_git_config(regex_include=".*")
finally:
    db.close()
