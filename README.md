# Pulp Manager

The Pulp Manager application is used to coordinate common Pulp
workflows and provide additional reporting capabilities about a
cluster of Pulp servers. It is designed to work with Pulp3.

We recommend that Pulp be operated in a primary/secondary setup. There
is a single Pulp instance known internally as the Pulp Master which
syncs repos from the Internet and can also have custom or internal
packages uploaded to it. Secondaries are then configured to sync these
snapshots and internal repos.

Pulp3 doesn't provide a method to schedule the synchronisation of
repos, and in some repository types (deb) may require multiple steps
to sync and update a repo's content. Pulp Manager provides the
coordination and reporting for this (along with other workflows),
rather than using a more generic management approach such as Ansible
orJenkins.

APIs are synchronous but usualy launch background jobs for
long-running processes. The main work of the application is done by RQ
workers. An RQ worker runs as a single process (although it does use
fork internally), however this still means there is nothing gained
from awaiting on the Database. Other libs such as the Hashicorp
Vault library are likewise not async. 

## Architecture

See ARCHITECTURE.md in docs folder

## Application configuration

An ini file is used to define application settings. A sample ini along
with explanation of sections is given below. File needs to be deployed
to /etc/pulp_manager/config.ini

```
[ca]
root_ca_file_path=/etc/pulp_manager/root.pem

[auth]
method=ldap
use_ssl=true
ldap_servers=dc.example.com
base_dn=DC=example,DC=com
default_domain=example.com
jwt_algorithm=HS256
jwt_token_lifetime_mins=480
admin_group=pulpmaster-rw

[pulp]
deb_signing_service=pulp_deb
banned_package_regex=bannedexample|another
internal_domains=example.com
git_repo_config=https://git.example.com/Pulp-Repo-Config
git_repo_config_dir=repo_config
password=password
internal_package_prefix=corp_
package_name_replacement_pattern=
package_name_replacement_rule=
remote_tls_validation=true

[redis]
host=redis
port=6379
db=0
max_page_size=24

[remotes]
sock_connect_timeout=120.0
sock_read_timeout=600.0

[paging]
default_page_size=50
max_page_size=20000

[vault]
vault_addr=http://127.0.0.1:8200
repo_secret_namespace=secrets-common
```

### ca

Defines Certificate Authority settings
- `root_ca_file_path`: Path to root ca file, which is applied to remotes that are synched over SSL

### auth

Defines authentication allowed against the API
- `method`: Type of auth to use, currently only LDAP is allowed
- `use_ssl`: Specifies if LDAPS should be used
- `ldap_servers`: Comma separate list of LDAP servers to use for authentication
- `base_dn`: Base Distinguished Name to search for users in when carrying out authentication
- `default_domain`: Netbios name of the Active Directory domain
- `jwt_algorithm`: Algorithm to use to encrypt JWT tokens
- `jwt_token_lifetime_mins`: Number of minutes JWT is valid for
- `admin_group`: Directory group user must be a member of to carry out priveldged actions agains the API

### pulp

Settings to apply to all pulp servers
- `deb_signing_service`: Name of the signing service to use to sign Release file of deb repos
- `banned_package_regex`: Regex of packages that should be removed from externally synched repos
- `internal_domains`: Comma separated list of domains that are internal. Defines when the root CA cert should be applied, along with steps in synchronisation that can be synched when synching from a Pulp Server
- `git_repo_config`: Repo that contains the config of Pulp repos that should exist on primary
- `git_repo_config_dir`: Directory in `git_repo_config` which contains the pulp repo config
- `remote_tls_validation`: Boolean whether to require TLS validation of remote hosts

### redis

Settings to connect to redis
- `host`: hostname of the redis server
- `port`: port to connect to redis on
- `db`: db number to use
- `max_page_size`: Used via API to define maximum number of results that can be pulled back from redis at once

### remotes

Settings to all remotes created/update by Pulp Manager
- `sock_connect_timeout`: aiohttp.ClientTimeout.sock_connect (q.v.) for download-connections
- `sock_read_timeout`: aiohttp.ClientTimeout.sock_read (q.v.) for download-connections

### paging

Default settings for paging on the API
- `default_page_size`: Default size of pages retrieved from API
- `max_page_size`: Maximum number of results that can be returned in a inslge page

### vault

Settings for how Pulp Manager interacts with the vault agent
- `vault_addr`: Address to use to communicate with the vault agent
- `repo_secret_namespace`: namespace which contains remote secrets. This is where RedHat Certs and keys should be placed as defined in the repo config at https://git.example.com/Pulp-Repo-Config

## Sync Configuration

A YAML file needs to provided which the app reads on start up, to
insert the pulp servers and repo group information into the DB. File
needs to be deployed to /etc/pulp_manager/pulp_config.yml

A sample configuration file is shown below:

```
pulp_servers:
  pulp3.example.com:
    credentials: example
    repo_config_registration:
        schedule: "0,15,30,45 * * * *"
        max_runtime: "20m"
    repo_groups:
      external_repos:
        schedule: "0 0 * * *"
        max_conccurent_sync: 2
        max_runtime: "6h"
    snapshot_support:
      max_concurrent_snapshots: 2

  pulp3slav1.example.com:
    credentials: example
    repo_groups:
      external_repos:
        schedule: "0 6 * * *"
        max_conccurent_sync: 2
        max_runtime: "6h"
        pulp_master: pulp3mast1.example.com

credentials:
  example:
    username: svc-linux-pulp-dapi
    vault_service_account_mount: service-accounts

repo_groups;
  external_repos:
    regex_include: ^ext-
```

The different sections are as follows:

### pulp_servers

This is a dict which contains the name of the pulp server that is to
be managed, with the value being a series of dicts that define the
credentials and repo groups to sync.

- `credentials`: The name of the credentials block to use to retrieve credentials from hasi corp vault for authenticating against hte Pulp Server API
- `repo_config_registration`: This is for use with pulp primaries. There is a git repo, which contains the base repos we expect to have on Pulp Servers (https://git.example.com/Pulp-Repo-Config). This repo defines remote repos that are using to sync external repos for the OS release along with internal repos. This parameter defines how often the config is checked out from git and re applied to the pulp server
  - `schedule`: cron syntax to define how often the job should run
  - `max_runtime`: how long the job should run for before it is cancelled
- `repo_groups`: Defines groups of repos that should be synched on a regular basis. The key is name of the repo group block to sync and the value is another dict which contains the options to use carrying out the syncs
  - `schedule`: cron syntax for how often the repo group should be synched
  - `max_concurrent_syncs`: How many repos should be synched at once when the job is run
  - `max_runtime`: How long the job should run for before it is cancelled
  - `pulp_primary` (Optional): If the pulp server is synching the repos from a pulp primary, specify the name of the pulp server. This needs to exist in the pulp_servers config so that the list of repos on the server can be retreived via the API
- `snapshot_support`: specifies if snapshots can be run against the pulp server, value is a dict
  - `max_concurrent_snapshots`: number of repos that can snapshotted simultaneously

### credentials

This is a dict which defines the name of credentials groups. The key is a dict which names the credential group and the value, is another dict which contains the configuration that pulp manager users to retrieve the credentials from HashiCorp vault

- `username`: username of credentials group to retreive
- `vault_service_account_mount`: vault service account path to retrieve the credentials form e.g. service-accounts
### repo_groups

This is a dict which defines a name for a set of repos, and then regular expressions to match repo names on. The repo groups are then applied to pulp server, which schedules and run times can be specified

- `regex_include` (Optional): regex to match repo names on that should be included for synchronisation
- `regex_exclude` (Optional): regex to match repo names that should be excluded from synchronisation. `regex_exclude` take precedence over `regex_include`, so if there is a repo that matches both regexes it would be excluded

# Development Info

## Development with DevContainers (Recommended)

This project includes a DevContainer configuration for consistent
development environments across different machines. DevContainers
provide a fully configured development environment with all necessary
dependencies, services, and tools pre-installed.

### Prerequisites
- Docker Desktop or Docker Engine
- Visual Studio Code with the Dev Containers extension (recommended)
- OR any IDE that supports DevContainers

### Getting Started with DevContainers

1. **Using VS Code (Recommended)**
   - Open the project in VS Code
   - When prompted, click "Reopen in Container" 
   - Or use Command Palette (F1) → "Dev Containers: Reopen in Container"
   - VS Code will build and start the container with all services

2. **Using Command Line**
   ```bash
   # Install devcontainer CLI
   npm install -g @devcontainers/cli
   
   # Open in devcontainer
   devcontainer open
   ```

The DevContainer includes:
- Python 3.10 with all project dependencies
- MariaDB 11.1.2 for the database
- Redis for caching and task queuing
- LDAP development libraries
- Pre-configured pytest with VS Code integration
- All required Python packages from requirements.txt

### Running Tests in DevContainer

Once inside the DevContainer:
```bash
# Run all tests
make t

# Run with coverage
make c

# Run specific test file
./venv/bin/pytest pulp_manager/tests/unit/test_job_manager.py -v

# Run lint
make l
```

## Alternative: Manual Development Setup

If you prefer not to use DevContainers, you can set up the development environment manually:

1. **Starting the Development Environment**

To initialize and start the services required for local development, execute the following command in your terminal:

```shell
make run-pulp-manager
```
This command orchestrates the setup by utilizing dockercompose-local.yml to start all necessary services. It also triggers the 
building of Docker images if they are not found or if there are updates to the images since the last build. 

For local authentication, the Pulp manager utilizes the password
specified for pulp3 in local_config.ini and the username defined in
local_pulp_config.yml. Note that this configuration is contingent upon
the is_local environment variable being set to true. (This can be
found in pulp_helpers.py)

2. **Port Forwarding (Manual Setup Only)**

If using the manual setup, forward port 8080 from your environment to
your local machine. With DevContainers, ports are automatically
forwarded as configured in devcontainer.json.

For manual setups or DevPods:
```shell
devpod tunnel <name of your devpod> -p 8080:8080
```

3. **Accessing the Application**  

Once the development environment is up, you can access the application through your web browser. Navigate to:

```
http://localhost:8080/docs
```

**Note**: With DevContainers, VS Code automatically handles port forwarding for ports 8080, 9300, 3306, and 6379 as configured in the devcontainer.json.
4. **Hot Reloading**  

The development environment is configured to support hot
reloading. This feature automatically refreshes your application as
soon as you make and save changes to the code. This means there's no
need to stop and restart the entire environment every time you modify
a file.


5. **Starting Pulp 3 Environment**  

For development that requires Pulp 3, you can start the Pulp 3 environment locally using Docker Compose. Run the following command in your terminal:
```
make run-pulp3
```
This command makes use of dockercompose-pulp3.yml to bring up the Pulp 3 services. It's particularly useful for testing integrations with Pulp 3 or when working on features that depend on Pulp 3 services.

### When to Use make run-pulp-manager Again:

**Modifying Dependencies**: If your changes involve updating, adding, or removing dependencies in your project, you will need to re-run the make run-pulp-manager command. This ensures that the new dependencies are correctly installed and integrated into your development environment.

**Major Configuration Changes**: Similarly, for major changes to the Docker configuration or other integral parts of the development setup that are not automatically applied through hot reloading, re-running make run-pulp-manager is necessary.

## Continuous Integration

This project uses GitHub Actions for CI/CD with DevContainer integration:

- **Automated Testing**: All tests run in the same DevContainer environment used for development
- **Linting**: Code quality checks with pylint
- **Coverage Reporting**: Test coverage analysis with pytest-cov
- **Multiple Test Strategies**: Both direct pytest and `make t` execution

The CI workflows are defined in `.github/workflows/`:
- `test.yml`: Quick test execution on pushes and PRs
- `ci.yml`: Comprehensive CI with linting, testing, and coverage reporting

See `.github/workflows/README.md` for detailed workflow documentation.

## Code Layout Overview

The main code for the application lives in the app directory and split into the following main folders:
- models: SQLAlchemy models which map back to database tables
- repositories: Classes that interact with the models. Each repository inherits from TableRepository, which contains generic operations for CRUD actions. On the filter method relationships directly attached to the entity can be eagerly loaded by specifying their name in the eager option. 1 model has 1 repository
- services: This contains the main business logic of the app, services will make use of multiple table repositories for interacting with the DB and also carry out the commits and rollbacks
- utils: Utilities common accross the app, e.g. logging 
