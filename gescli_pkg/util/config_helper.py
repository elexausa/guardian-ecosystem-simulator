import configparser
import logging
import os

from .daemon_helper import DAEMON_ADDRESS, DAEMON_PORT

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

# Open version file
version_file = open(os.path.join(__location__, '../VERSION'))

# Get version number
version = version_file.read().strip()

# Define logger
logger = logging.getLogger(__name__)

# Filename
CONFIG_FILE = os.path.join(__location__, '../config.ini')

def load():
    """Load configuration from configuration file.
    """
    logger.info('Loading configuration')
    logger.debug('Loading configuration from {}'.format(CONFIG_FILE))

    # Load file
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)

    # Get IP and port from file
    DAEMON_ADDRESS = config["daemon"]["address"]
    DAEMON_PORT = config["daemon"]["port"]

    logger.info('Configuration loaded')
    logger.debug('Pointing to GES daemon at {address}:{port}.'.format(address=DAEMON_ADDRESS, port=DAEMON_PORT))
