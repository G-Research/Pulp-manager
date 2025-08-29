"""Returns a config object containing default settings
"""

import os
import configparser

# This needs some improving with actual retries but will do
# during development
CONFIG_FILE = "/etc/pulp_manager/config.ini"

if "PULP_MANAGER_CONFIG_PATH" in os.environ:
    CONFIG_FILE = os.environ["PULP_MANAGER_CONFIG_PATH"]

CONFIG = configparser.ConfigParser()
CONFIG.read(CONFIG_FILE)
