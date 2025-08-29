"""Main entry point into starting up API, and ensuring scheduled jobs are started
"""
#pylint: disable=raise-missing-from

import os
import traceback

from fastapi import FastAPI, HTTPException
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html
)
from fastapi.staticfiles import StaticFiles

from pulp_manager.app.database import session
from pulp_manager.app.job_manager import JobManager
from pulp_manager.app.middleware import RequestContextMiddleware, get_request_id
from pulp_manager.app.route import LoggingRoute
from pulp_manager.app.routers.v1 import (
    pulp_server_v1_router, task_v1_router, rq_jobs_v1_router, auth_v1_router
)
from pulp_manager.app.services import PulpConfigParser
from pulp_manager.app.utils import log


# work out the path to the static dir for JS and CS
STATIC_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "static")
PULP_SYNC_CONFIG = "/etc/pulp_manager/pulp_config.yml"

if "PULP_SYNC_CONFIG_PATH" in os.environ:
    PULP_SYNC_CONFIG = os.environ["PULP_SYNC_CONFIG_PATH"]
    log.info(f"Using PULP_SYNC_CONFIG_PATH: {PULP_SYNC_CONFIG}")


def parse_config(pulp_sync_config: str):
    """Parses config from the specified config file and then updates the database
    and rq scheduled jobs. This needs some kind of locking in the future when multiple
    APIs are being spun up

    :param pulp_sync_config: Path to the yaml file that contains the pulp sync config
    :type pulp_sync_config: str
    """

    try:
        log.info("Carrying out Pulp Manager prereqs")
        db = session()
        log.info("Parsing repo sync config")
        pulp_config_parser = PulpConfigParser(db)
        pulp_config_parser.load_config(pulp_sync_config)
        log.info("Setting up RQ scheduled jobs")
        job_manager = JobManager(db)
        job_manager.setup_schedules()
    except Exception:
        log.error("Failed to setup Pulp Manager prereqs")
        log.error(traceback.format_exc())
        raise
    finally:
        db.close()


def get_application():
    """Returns the instance of the fastapi application to run
    """

    if os.path.isfile(PULP_SYNC_CONFIG):
        log.info(f"Config file found at {PULP_SYNC_CONFIG}.")
        if "PULP_MANAGER_SKIP_PARSER_CONFIG" in os.environ:
            log.info("Skipping config parse due to 'PULP_MANAGER_SKIP_PARSER_CONFIG'.")
        else:
            try:
                parse_config(PULP_SYNC_CONFIG)
                log.info("Successfully parsed the Pulp sync config.")
            except Exception as e:
                log.error(f"Failed to parse the Pulp sync config: {e}")
    else:
        log.warning(f"Config missing at {PULP_SYNC_CONFIG}; no schedules updated.")
        if "PULP_MANAGER_SKIP_PARSER_CONFIG" in os.environ:
            log.info("Skipping config parsing as 'PULP_MANAGER_SKIP_PARSER_CONFIG' is set.")
        else:
            log.info("The 'PULP_MANAGER_SKIP_PARSER_CONFIG' environment variable is not set.")

    # pylint: disable=redefined-outer-name
    app = FastAPI(
        title='Pulp Manager', version='0.10.0', docs_url=None, redoc_url=None,
        description="Pulp Manager is used to orchestrate the pulp servers in GR"
    )
    # Test methods below to make sure the serving of static content worked
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.add_middleware(RequestContextMiddleware)
    app.include_router(auth_v1_router)
    app.include_router(pulp_server_v1_router)
    app.include_router(task_v1_router)
    app.include_router(rq_jobs_v1_router)
    app.router.route_class = LoggingRoute
    return app

#pylint: disable=invalid-name
app = None

try:
    log.info('Starting Pulp Manger application')
    app = get_application()
except Exception:
    log.error("Pulp Manager failed to start")
    log.error(traceback.format_exc())
    raise


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Setup for hosting swagger css and js locally. Carbon copy of
    https://fastapi.tiangolo.com/tutorial/static-files/
    """

    try:
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=app.title + " - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="/static/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui.css",
        )
    except Exception as exception:
        log.exception('Swagger UI failed to load')
        log.exception(str(exception))
        log.exception(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occured, request_id: {get_request_id()}"
        )


@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    """Setup for the swagger UI redirect as given at
    https://fastapi.tiangolo.com/tutorial/static-files/
    """

    try:
        return get_swagger_ui_oauth2_redirect_html()
    except Exception as exception:
        log.exception('Swagger UI redirect failed')
        log.exception(str(exception))
        log.exception(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occured, request_id: {get_request_id()}"
        )


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    """Setup for hosting redoc locally, as given at
    https://fastapi.tiangolo.com/tutorial/static-files/
    """

    try:
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=app.title + " - ReDoc",
            redoc_js_url="/static/redoc.standalone.js",
        )
    except Exception as exception:
        log.exception('Redoc failed to load')
        log.exception(str(exception))
        log.exception(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occured, request_id: {get_request_id()}"
        )
