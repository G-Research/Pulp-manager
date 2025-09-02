# Architecture

Pulp Manager's architecture has five components to it. REST API, Exporter, Worker, Scheduler and rq-dashboard (external project). Each of the components can be scaled out horizontally for high availability and/or additional capacity. There is some additional work to be done so that Pulp Manager can communicate with Sentinel so that can be highly available as it is used by the scheduler and the workers

![PulpManagerArchitecture](PulpManagerArchitecture.png)

## API

The API is a FastAPI application and hosted via gunicorn. It hosts the following entry points:
- /v1 - where all the API endpoints are
- /docs - documentation about the various API endpoints

The API is hosted on port 433

## exporter

The exporter is written using the Python prometheus client and is used to serve metrics about the state pulp server and the health of the repos that are synched on the pulp server. The exporter is hosted on port 9300. The exporter application is separate to the API, because there is a Fast API Prometheus exporter (currently not in use) that is available, and it was felt it was better to keep the custom exporter separate and avoid any potential integration/collision problems

## rq-dashboard

RQ Dashboard is an externally developed pypi application that provides a basic UI, which shows history of previosuly run RQ jobs. The RQ dashboard has no auth, and has options to empty the worker queus, so when setting up a loadbalancer to access the dashboard it can be setup to only permit access via gets.

## worker

The worker component uses RQ to run background/long running tasks. To increase concurrency additional workers can be added. One worker can only execute one task at a time, however some tasks maybe written to get out multiple repo tasks at once. The workers rely on Redis to pick up tasks that need to be carried out, and also write data about the tasks to the mariadb, where pulp server health, and repo sync health is calculated.

## scheduler

The scheduler component is an additional RQ extension that adds tasks to the RQ redis queues to be picked up via the workers. When Pulp Manager starts it sets up a series recuring tasks that need to run based on the configuration in pulp_config.yml, this is added to the redis store, which the scheduler reads to add work to the queue that needs to run
