#!/bin/bash

set -euo pipefail

# script to assist with starting pulp manager and for migrating container database
# can be used as a command/entry point to run the application.
# Designed for use in pulp manager container

print_help(){
    echo "Starts the relevant components of the pulp manager app"
    echo ""
    echo "Syntax: pulp-manager.sh [options]"
    echo ""
    echo "Options:"
    echo "-m|--migrate: applies database migrations to the pulp manager app"
    echo "-a|--api: starts the web api"
    echo "-w|--worker: starts an instance of a worker"
    echo "-s|--scheduler: starts an instance of the scheduler for setting up regular background tasks"
    echo "-e|--exporter: starts an instance of the exporter"
    echo "-d|--rq-dashboard: starts an instance of the rq dashboard"
    echo "--redis-url: redis url to bind to. Only used for rq-dashboard"
    echo "--no-ssl: Optional for -a. Starts the web api without SSL"
    echo "--dev: Starts the application in development mode with hot reloading (Only applicable with -a)"
}

DEVELOPMENT=false
NUM_ACTIONS=0
ACTIONS_GIVEN=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--migrate)
            MIGRATE=true
            ACTIONS_GIVEN="${ACTIONS_GIVEN}migrate,"
            shift
            ;;
        -a|--api)
            WEB_API=true
            ACTIONS_GIVEN="${ACTIONS_GIVEN}api,"
            shift
            ;;
        -w|--worker)
            WORKER=true
            ACTIONS_GIVEN="${ACTIONS_GIVEN}worker,"
            shift
            ;;
        -s|--scheduler)
            SCHEDULER=true
            ACTIONS_GIVEN="${ACTIONS_GIVEN}scheduler,"
            shift
            ;;
        -e|--exporter)
            EXPORTER=true
            ACTIONS_GIVEN="${ACTIONS_GIVEN}exporter,"
            shift
            ;;
        -d|--rq-dashboard)
            RQ_DASHBOARD=true
            ACTIONS_GIVEN="${ACTIONS_GIVEN}dashboard,"
            shift
            ;;
        --redis-url)
            REDIS_URL=$2
            shift 2
            ;;
        --no-ssl)
            NO_SSL=true
            shift
            ;;
        --dev)
            DEVELOPMENT=true
            shift
            ;;
        *)
            echo "Unknown argument $1"
            print_help
            exit 1
            ;;
    esac
done

VENV_PATH="/opt/venv/bin/"
/pulp_manager/wait_db.sh


if [[ ${MIGRATE+x} ]]; then
    "${VENV_PATH}alembic" upgrade head || exit $?
fi

if [[ ${WEB_API+x} ]]; then
    if [[ "$DEVELOPMENT" = "true" ]]; then
        "${VENV_PATH}uvicorn" pulp_manager.app.main:app --reload --host 0.0.0.0 --port 8000 &
    else
        if [[ ${NO_SSL+x} ]]; then
            "${VENV_PATH}gunicorn" pulp_manager.app.main:app --bind 0.0.0.0:8000 -k uvicorn.workers.UvicornWorker --workers 4 &
        else
            "${VENV_PATH}gunicorn" pulp_manager.app.main:app --bind 0.0.0.0:8000 --keyfile /pulp_manager/server.key --certfile /pulp_manager/server.pem -k uvicorn.workers.UvicornWorker --workers 4 &
        fi
    fi
fi

if [[ ${WORKER+x} ]]; then
    PYTHONPATH=. "${VENV_PATH}python" pulp_manager/app/worker.py &
fi

if [[ ${SCHEDULER+x} ]]; then
    PYTHONPATH=. "${VENV_PATH}python" pulp_manager/app/scheduler.py &
fi

if [[ ${EXPORTER+x} ]]; then
    PYTHONPATH=. "${VENV_PATH}python" pulp_manager/app/prometheus_pulp_manager_data.py &
fi

if [[ ${RQ_DASHBOARD+x} ]]; then
    if [[ -z ${REDIS_URL+x}  ]]; then
        print_help
        exit 1
    fi

    "${VENV_PATH}rq-dashboard" --bind 0.0.0.0 --redis-url ${REDIS_URL} &
fi

# Wait for all background processes to complete
wait
