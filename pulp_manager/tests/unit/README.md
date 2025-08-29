# unit_tests

The unit tests mock out all external systems that are talked to by the service layers.
This means current access to a database isn't needed to run the unit tests, dury still out if the database should be being mocked out.

To mock out the database, a MockRepository is used which inheirts from ITableRepository. From the MockRepository a mock repository is then created for each database entity type, just as is done in the proper TableRepoistory used by the app. For the mock repository to work a MockSession needs to be passed through, which can be preloaded with a set of entities to fake some data that would be in the DB. To use the MockRepositories you just patch out the Repository that is in use for the service, best place to usually do this is the setup_method.

The mock repository has several limitations (which shouldn't cause too many issues, if this starts becoming quite problematic the mock repositories may have to be done away with):
- Cascades are not carried out on Foreign keys where it has been setup for updates and deletes
- Entities are not state tracked so if relationships have been eager loaded to have the correct entries after deletion the eager load must be re-carried
- Currently the only type of eager loading supported is from parent to child table
