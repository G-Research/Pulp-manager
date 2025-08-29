
pulp3_bindings
===================

This binding library does not expose the complete set of API endpoints that are avaialble in Pulp, just the ones that are needed for Pulp Manager. Bindings for objects in Pulp are written using pydantic, giving real objects that can be used instead of manipulating dictionaries.

There is a Pulp3Client object which is used for holding credentials to auth against the API.

Method definitions for resource types take the following format
```
get_distribution(client: Pulp3Client, href: str, params: dict=None)
new_distribution(client: Pulp3Client, distribution: Distribution)
update_distribution(client: Pulp3Client, distribution: Distribution)
update_distribution_monitor(client: Pulp3Client, distribution: Distribution,...)
```

API calls that would return a task object also have an ```_monitor``` method which monitors creation/updates to completion. When using ```new_``` or ```update_object_monitor```. The object that is passed through has its values updated, rather than returning a new object.

Examples:
```
>>> client = Pulp3Client('pulp.domain.local', 'username', 'password')
>>> remote = RpmRemote(**{'name': 'Test-Remote', 'url': 'https://url.domain.local', 'policy': 'immediate'})
>>> remote.pulp_href
>>> new_remote(client, remote)
>>> remote.pulp_href
'/pulp/api/v3/remotes/rpm/rpm/adbc...'
```
