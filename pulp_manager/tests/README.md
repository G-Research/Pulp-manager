# Testing

Testing is split between database and unit tests.
* Database tests - Designed to be run against a database server, and validate that queries return the results expected, and foreign key and index constraints hold
* Unit Tests - Designed for testing the service layers. When testing the service layers the table repositories are mocked out resulting in no calls being made to a database
* API tests - Whilst API testing isn't a particular test type and they are more similar to unit tests, it allows it to be separated out from the services layer so that a database connection isn't needed for tests, and it doesn't have to interrupt a sample database
