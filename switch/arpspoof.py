"""
ARPSPOOF component switch
For more details about this component, please refer to the documentation
"""
import logging
import socket
import voluptuous as vol

from homeassistant.components.switch import (
    SwitchDevice, PLATFORM_SCHEMA, ENTITY_ID_FORMAT)
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    CONF_IP_ADDRESS, CONF_DEVICES, CONF_FRIENDLY_NAME, CONF_ICON, STATE_ON,
    STATE_OFF)

_LOGGER = logging.getLogger(__name__)

DATA_ARPSPOOF = "arpspoof"

DEVICES_SCHEMA = vol.Schema({
    vol.Required(CONF_IP_ADDRESS): cv.string,
    vol.Optional(CONF_FRIENDLY_NAME): cv.string,
    vol.Optional(CONF_ICON): cv.icon,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES): vol.Schema({cv.slug: DEVICES_SCHEMA}),
})


def is_valid_ipv4_address(address):
    try:
        socket.inet_pton(socket.AF_INET, address)
    except AttributeError:  # no inet_pton here, sorry
        try:
            socket.inet_aton(address)
        except socket.error:
            return False
        return address.count('.') == 3
    except socket.error:  # not a valid address
        return False

    return True


def setup_platform(hass, config, add_devices,
                   discovery_info=None):
    """Setup"""
    _LOGGER.info("Starting up")

    if DATA_ARPSPOOF not in hass.data:
        _LOGGER.error("ARP component not initialised!")
        return False

    devices = config.get(CONF_DEVICES, {})
    switches = []
    data = hass.data[DATA_ARPSPOOF]

    for object_id, device_config in devices.items():
        ip_address = device_config.get(CONF_IP_ADDRESS)
        friendly_name = device_config.get(CONF_FRIENDLY_NAME)

        if is_valid_ipv4_address(ip_address):
            _LOGGER.debug("Adding IP '%s' as switch '%s'",
                          ip_address, friendly_name)

            switches.append(
                ArpSpoofSwitch(
                    data,
                    object_id,
                    friendly_name,
                    ip_address,
                    device_config.get(CONF_ICON)
                )
            )
        else:
            _LOGGER.debug("IP '%s' is not valid IP address", ip_address)

    if not switches:
        _LOGGER.error("No devices added")
        return False

    add_devices(switches)


class ArpSpoofSwitch(SwitchDevice):
    """Representation of a ArpSpoof switch."""

    def __init__(self, instance, object_id, friendly_name, ip_address,
                 icon):
        """Initialize the switch."""
        self._name = friendly_name
        self._ip_address = ip_address
        self._state = False
        self._icon = icon
        self.entity_id = ENTITY_ID_FORMAT.format(object_id)
        self._instance = instance

        _LOGGER.debug("Switch INIT")

    @property
    def should_poll(self):
        """No polling needed for a demo switch."""
        return False

    @property
    def icon(self):
        """Return the icon to use for device if any."""
        return self._icon

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    def update(self):
        """Update the switch value."""
        return False

    @property
    def assumed_state(self):
        """Return if the state is based on assumptions."""
        return False

    @property
    def is_on(self):
        """Return state of entity is on."""
        return self._state

    def turn_on(self):
        """Turn the entity on."""
        self._state = self._instance.add_device(self._ip_address)
        self.schedule_update_ha_state()

    def turn_off(self):
        """Turn the entity off."""
        # API returns True of successful
        self._state = self._instance.remove_device(self._ip_address)
        self.schedule_update_ha_state()
