import asyncio
from datetime import timedelta
import logging
from xml.parsers.expat import ExpatError

import async_timeout
import aiohttp
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_MONITORED_CONDITIONS, TEMP_FAHRENHEIT, TEMP_CELSIUS, ATTR_ATTRIBUTION)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import (
    async_track_point_in_utc_time, async_track_time_interval)
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

CONF_ATTRIBUTION = "Weather forecast delivered by your WD Clientraw enabled " \
    "weather station."

SENSOR_TYPES = {
    'dewpoint': ['Dewpoint (°C)', TEMP_CELSIUS],
    'heat_index': ['Heat index (°C)', TEMP_CELSIUS],
    'temp': ['Temperature (°C)', TEMP_CELSIUS],
    'humidex': ['Humidex (°C)', TEMP_CELSIUS],
    'wind_degrees': ['Wind Degrees', '°'],
    'wind_dir': ['Wind Direction', None],
    'wind_gust_kph': ['Wind Gust (km/h)', 'km/h'],
    'wind_gust_mph': ['Wind Gust (mph)', 'mph'],
    'wind_kph': ['Wind Speed (km/h)', 'km/h'],
    'wind_mph': ['Wind Speed (mph)', 'mph'],
    'symbol': ['Symbol', None],
    'daily_rain': ['Daily Rain', 'mm'],
    'rain_rate': ['Rain Rate', 'mm'],
    'pressure': ['Pressure', 'hPa'],
    'humidity': ['Humidity', '%'],
    'cloud_height_m': ['Cloud Height (m)', 'm'],
    'cloud_height_ft': ['Cloud Height (ft)', 'ft']
}

CONF_URL = 'url'
CONF_INTERVAL = 'interval'
CONF_NAME = 'name'
DEFAULT_NAME = 'clientraw'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_MONITORED_CONDITIONS, default=[]):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES.keys())]),
    vol.Required(CONF_URL, default=[]): cv.url,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_INTERVAL, default=15):
        vol.All(vol.Coerce(int), vol.Range(min=1, max=59)),
})


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Setup the sensor platform."""

    url = config.get(CONF_URL)
    interval = config.get(CONF_INTERVAL)
    name = config.get(CONF_NAME)
    
    _LOGGER.debug("Clientraw setup interval %s", interval)

    dev = []
    for sensor_type in config[CONF_MONITORED_CONDITIONS]:
        dev.append(ClientrawSensor(sensor_type, name))
    async_add_devices(dev)

    weather = ClientrawData(hass, url, dev)
    # Update weather per interval
    async_track_time_interval(hass, weather.async_update,
                              timedelta(minutes=interval, seconds=0))
    yield from weather.async_update()


class ClientrawSensor(Entity):
    """Representation of an clientraw sensor."""

    def __init__(self, sensor_type, name):
        """Initialize the sensor."""
        self.client_name = name
        self._name = SENSOR_TYPES[sensor_type][0]
        self.type = sensor_type
        self._state = None
        self._unit_of_measurement = SENSOR_TYPES[self.type][1]

    @property
    def name(self):
        """Return the name of the sensor."""
        return '{} {}'.format(self.client_name, self._name)

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_ATTRIBUTION: CONF_ATTRIBUTION,
        }

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement


class ClientrawData(object):
    """Get the latest data and updates the states."""

    def __init__(self, hass, url, devices):
        """Initialize the data object."""
        self._url = url
        self.devices = devices
        self.data = {}
        self.hass = hass

    @asyncio.coroutine
    def async_update(self, *_):
        """Get the latest data"""
        def try_again(err: str):
            """Retry in 5 minutes."""
            _LOGGER.warning('Fetching url failed, retrying in 5 min: %s', err)
            nxt = dt_util.utcnow() + timedelta(minutes=5)
            if nxt.minute >= 5:
                async_track_point_in_utc_time(
                    self.hass, self.async_update, nxt)

        resp = None
        try:
            websession = async_get_clientsession(self.hass)
            with async_timeout.timeout(10, loop=self.hass.loop):
                resp = yield from websession.get(self._url)
            if resp.status != 200:
                try_again('{} returned {}'.format(resp.url, resp.status))
                return
            text = yield from resp.text()

        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            try_again(err)
            return

        # finally:
        #     if resp is not None:
        #         self.hass.async_add_job(resp.release())

        try:
            self.data = text.split(' ')

            if len(self.data) < 115:
                raise ValueError('Could not parse the file')
        except (ExpatError, IndexError) as err:
            try_again(err)
            return

        tasks = []

        _LOGGER.info("Updating states...")

        # Update all devices
        for dev in self.devices:
            new_state = None

            if dev.type == 'symbol':
                new_state = int(self.data[48])

            elif dev.type == 'daily_rain':
                new_state = float(self.data[7])

            elif dev.type == 'rain_rate':
                new_state = float(self.data[10])

            elif dev.type == 'temp':
                new_state = float(self.data[4])

            elif dev.type == 'wind_kph':
                knots = float(self.data[1])
                new_state = round(knots * 1.85166, 2)

            elif dev.type == 'wind_mph':
                knots = float(self.data[1])
                kmh = (knots * 1.85166)
                new_state = round(0.6214 * kmh, 2)

            elif dev.type == 'wind_gust_kph':
                knots = float(self.data[2])
                new_state = round(knots * 1.85166, 2)

            elif dev.type == 'wind_gust_mph':
                knots = float(self.data[2])
                kmh = (knots * 1.85166)
                new_state = round(0.6214 * kmh, 2)

            elif dev.type == 'pressure':
                new_state = float(self.data[6])

            elif dev.type == 'wind_degrees':
                new_state = float(self.data[3])

            elif dev.type == 'wind_dir':
                direction = float(self.data[3])
                val = int((direction / 22.5) + .5)
                arr = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                       "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
                new_state = arr[(val % 16)]

            elif dev.type == 'humidity':
                new_state = float(self.data[5])

            elif dev.type == 'cloud_height_m':
                new_state = float(self.data[73])

            elif dev.type == 'cloud_height_ft':
                meters = float(self.data[73])
                new_state = round(meters / 0.3048, 2)

            elif dev.type == 'dewpoint':
                new_state = float(self.data[72])

            elif dev.type == 'heat_index':
                new_state = float(self.data[112])

            elif dev.type == 'humidex':
                new_state = float(self.data[44])

            _LOGGER.debug("%s %s", dev.type, new_state)

            # pylint: disable=protected-access
            if new_state != dev._state:
                dev._state = new_state
                tasks.append(dev.async_update_ha_state())

        if tasks:
            yield from asyncio.wait(tasks, loop=self.hass.loop)
