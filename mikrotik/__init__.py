import asyncio
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_PORT, CONF_NAME)

import librouteros

__version__ = '1.0.0'

REQUIREMENTS = ['librouteros==1.0.4']

DOMAIN = "mikrotik"
DEFAUL_PORT = 8728

SERVICE_COMMAND_NAME = "run_script"

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_PORT): cv.port,
    }),
}, extra=vol.ALLOW_EXTRA)

SERVICE_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string
})


@asyncio.coroutine
def async_setup(hass, config):
    """Initialize of Mikrotik component."""
    conf = config[DOMAIN]
    host = conf.get(CONF_HOST)
    username = conf.get(CONF_USERNAME)
    password = conf.get(CONF_PASSWORD, "")
    port = conf.get(CONF_PORT, DEFAUL_PORT)

    _LOGGER.info("Setup")

    @asyncio.coroutine
    def run_script(call):
        """Run script service."""
        req_script = call.data.get(CONF_NAME)

        _LOGGER.debug("Sending request to run '%s' script",
                      req_script)
        try:
            client = librouteros.connect(
                host,
                username,
                password,
                port=port
            )

            try:
                scripts = client(cmd='/system/script/print')

                for script in scripts:
                    try:
                        _LOGGER.debug("Script found: %s, id: %s, invalid: %s",
                                      script.get('name'),
                                      script.get('.id'),
                                      script.get('invalid'))

                        if req_script == script.get('name') and \
                                not script.get('invalid'):
                            _LOGGER.info("Running script id: %s",
                                         script.get('.id'))

                            params = {'.id': script.get('.id')}
                            run = client(cmd='/system/script/run', **params)

                    except Exception as e:
                        _LOGGER.error("Run script error: %s", str(e))

            except (librouteros.exceptions.TrapError,
                    librouteros.exceptions.MultiTrapError,
                    librouteros.exceptions.ConnectionError):
                _LOGGER.error("Command error")

        except (librouteros.exceptions.TrapError,
                librouteros.exceptions.MultiTrapError,
                librouteros.exceptions.ConnectionError) as api_error:
            _LOGGER.error("Connection error: %s", api_error)

    hass.services.async_register(
        DOMAIN, SERVICE_COMMAND_NAME, run_script,
        schema=SERVICE_SCHEMA)

    return True
