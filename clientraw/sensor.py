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
    CONF_MONITORED_CONDITIONS, TEMP_CELSIUS, TEMP_FAHRENHEIT, PRESSURE_HPA,
    PRESSURE_INHG, LENGTH_METERS, LENGTH_FEET, LENGTH_INCHES, ATTR_ATTRIBUTION)
from homeassistant.util import dt as dt_util
from homeassistant.util.pressure import convert as convert_pressure
from homeassistant.util.temperature import convert as convert_temperature
from homeassistant.util.distance import convert as convert_distance
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import (async_track_utc_time_change,
                                         async_call_later)

__version__ = '1.0.0'

_LOGGER = logging.getLogger(__name__)

CONF_ATTRIBUTION = "Weather forecast delivered by your WD Clientraw enabled " \
    "weather station."

SENSOR_TYPES = {
    'dewpoint': ['Dewpoint', TEMP_CELSIUS, TEMP_FAHRENHEIT, 'mdi:weather-fog'],
    'heat_index': ['Heat index', TEMP_CELSIUS, TEMP_FAHRENHEIT,
                   'mdi:thermometer'],
    'temp': ['Temperature', TEMP_CELSIUS, TEMP_FAHRENHEIT, 'mdi:thermometer'],
    'humidex': ['Humidex', TEMP_CELSIUS, TEMP_FAHRENHEIT, 'mdi:thermometer'],
    'wind_degrees': ['Wind Degrees', '°', '°', 'mdi:subdirectory-arrow-right'],
    'wind_dir': ['Wind Direction', None, None, 'mdi:subdirectory-arrow-right'],
    'wind_gust': ['Wind Gust', 'km/h', 'mph', 'mdi:weather-windy'],
    'wind_speed': ['Wind Speed', 'km/h', 'mph', 'mdi:weather-windy-variant'],
    'symbol': ['Symbol', None, None, 'mdi:triangle-outline'],
    'daily_rain': ['Daily Rain', 'mm', LENGTH_INCHES, 'mdi:weather-rainy'],
    'rain_rate': ['Rain Rate', 'mm', LENGTH_INCHES, 'mdi:weather-rainy'],
    'pressure': ['Pressure', PRESSURE_HPA, PRESSURE_INHG, 'mdi:trending-up'],
    'humidity': ['Humidity', '%', '%', 'mdi:water-percent'],
    'cloud_height': ['Cloud Height', LENGTH_METERS, LENGTH_FEET,
                     'mdi:cloud-outline'],
    'forecast': ['Forecast', None, None, "mdi:card-text-outline"]
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


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up the Clientraw sensor."""
    url = config.get(CONF_URL)
    interval = config.get(CONF_INTERVAL)
    name = config.get(CONF_NAME)

    _LOGGER.debug("Clientraw setup interval %s", interval)

    dev = []
    for sensor_type in config[CONF_MONITORED_CONDITIONS]:
        dev.append(ClientrawSensor(
            hass.config.units.is_metric, sensor_type, name))
    async_add_entities(dev)

    weather = ClientrawData(hass, url, interval, dev)
    # Update weather per interval
    async_track_utc_time_change(hass, weather.async_update,
                                minute=interval, second=0)
    await weather.async_update()


class ClientrawSensor(Entity):
    """Representation of an clientraw sensor."""

    def __init__(self, is_metric, sensor_type, name):
        """Initialize the sensor."""
        self.client_name = name
        self.type = sensor_type
        self._name = SENSOR_TYPES[sensor_type][0]
        self._state = None
        self._metric_unit_of_measurement = SENSOR_TYPES[self.type][1]
        self._imperial_unit_of_measurement = SENSOR_TYPES[self.type][2]
        self._icon = SENSOR_TYPES[self.type][3]
        self._is_metric = is_metric

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

        if self._is_metric:
            return self._metric_unit_of_measurement
        else:
            return self._imperial_unit_of_measurement

    @property
    def icon(self):
        """Return the icon of this entity, if any."""
        return self._icon


class ClientrawData(object):
    """Get the latest data and updates the states."""

    def __init__(self, hass, url, interval, devices):
        """Initialize the data object."""
        self._url = url
        self.devices = devices
        self.data = {}
        self.hass = hass
        self._interval = interval

    async def async_update(self, *_):
        """Get the latest data"""

        def try_again(err: str):
            """Retry"""
            _LOGGER.error("Will try again shortly: %s", err)
            async_call_later(self.hass, 2 * 60, self.async_update)
        try:
            websession = async_get_clientsession(self.hass)
            with async_timeout.timeout(10, loop=self.hass.loop):
                resp = await websession.get(self._url)
            if resp.status != 200:
                try_again('{} returned {}'.format(resp.url, resp.status))
                return
            text = await resp.text()

        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            try_again(err)
            return

        try:
            self.data = text.split(' ')

            if len(self.data) < 115:
                raise ValueError('Could not parse the file')
        except (ExpatError, IndexError) as err:
            try_again(err)
            return

        if not self.data:
            return

        # Update all devices
        tasks = []

        for dev in self.devices:
            new_state = None

            if dev.type == 'symbol':
                new_state = int(self.data[48])

            elif dev.type == 'daily_rain':
                rain = float(self.data[7])

                if not self.hass.config.units.is_metric:
                    rain = rain * 0.0393700787

                new_state = round(rain, 2)

            elif dev.type == 'rain_rate':
                rate = float(self.data[10])

                if not self.hass.config.units.is_metric:
                    rate = rate * 0.0393700787

                new_state = round(rate, 2)

            elif dev.type == 'temp':
                temperature = float(self.data[4])

                if not self.hass.config.units.is_metric:
                    temperature = convert_temperature(
                        temperature, TEMP_CELSIUS, TEMP_FAHRENHEIT)

                new_state = round(temperature, 2)

            elif dev.type == 'wind_speed':
                speed = float(self.data[1])

                if self.hass.config.units.is_metric:
                    new_state = speed * 1.85166
                else:
                    new_state = speed * 1.1507794

                new_state = round(speed, 2)

            elif dev.type == 'wind_gust':
                gust = float(self.data[2])

                if self.hass.config.units.is_metric:
                    new_state = gust * 1.85166
                else:
                    new_state = gust * 1.1507794

                new_state = round(gust, 2)

            elif dev.type == 'pressure':
                pressure = float(self.data[6])

                if not self.hass.config.units.is_metric:
                    pressure = round(convert_pressure(
                        pressure, PRESSURE_HPA, PRESSURE_INHG), 2)

                new_state = round(pressure, 2)

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

            elif dev.type == 'cloud_height':
                height = float(self.data[73])

                if not self.hass.config.units.is_metric:
                    height = convert_distance(
                        height, LENGTH_METERS, LENGTH_FEET)

                new_state = round(height, 2)

            elif dev.type == 'dewpoint':
                temperature = float(self.data[72])

                if not self.hass.config.units.is_metric:
                    temperature = convert_temperature(
                        temperature, TEMP_CELSIUS, TEMP_FAHRENHEIT)

                new_state = round(temperature, 2)

            elif dev.type == 'heat_index':
                temperature = float(self.data[112])

                if not self.hass.config.units.is_metric:
                    temperature = convert_temperature(
                        temperature, TEMP_CELSIUS, TEMP_FAHRENHEIT)

                new_state = round(temperature, 2)

            elif dev.type == 'humidex':
                temperature = float(self.data[44])

                if not self.hass.config.units.is_metric:
                    temperature = convert_temperature(
                        temperature, TEMP_CELSIUS, TEMP_FAHRENHEIT)

                new_state = round(temperature, 2)

            elif dev.type == 'forecast':
                val = int(self.data[15])
                arr = ["sunny", "clearnight", "cloudy", "cloudy2",
                       "night cloudy", "dry", "fog", "haze", "heavyrain",
                       "mainlyfine", "mist", "night fog", "night heavyrain",
                       "night overcast", "night rain", "night showers",
                       "night snow", "night", "thunder", "overcast",
                       "partlycloudy", "rain", "rain2", "showers2", "sleet",
                       "sleetshowers", "snow", "snowmelt", "snowshowers2",
                       "sunny", "thundershowers", "thundershowers2",
                       "thunderstorms", "tornado", "windy", "stopped",
                       "rainning", "wind + rain"]
                new_state = arr[(val)] if val < len(arr) else "unknown"

            _LOGGER.debug("%s %s", dev.type, new_state)

            # pylint: disable=protected-access
            if new_state != dev._state:
                dev._state = new_state
                tasks.append(dev.async_update_ha_state())

        if tasks:
            await asyncio.wait(tasks, loop=self.hass.loop)

        async_call_later(self.hass, self._interval * 60, self.async_update)
