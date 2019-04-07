"""
ARPSPOOF component switch
For more details about this component, please refer to the documentation
"""
import logging
import voluptuous as vol

from homeassistant.components.switch import (
    SwitchDevice, PLATFORM_SCHEMA, ENTITY_ID_FORMAT)
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    CONF_ADDRESS, CONF_DEVICES, CONF_FRIENDLY_NAME, CONF_ICON, STATE_ON,
    STATE_OFF)

REQUIREMENTS = ['validators==0.12.0']

_LOGGER = logging.getLogger(__name__)

DATA_ARPSPOOF = "arpspoof"

DEVICES_SCHEMA = vol.Schema({
    vol.Required(CONF_ADDRESS): cv.string,
    vol.Optional(CONF_FRIENDLY_NAME): cv.string,
    vol.Optional(CONF_ICON): cv.icon,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES): vol.Schema({cv.slug: DEVICES_SCHEMA}),
})


def setup_platform(hass, config, add_devices,
                   discovery_info=None):
    """Setup"""
    _LOGGER.debug("Starting up")

    import validators

    if DATA_ARPSPOOF not in hass.data:
        _LOGGER.error("ARP component not initialised!")
        return False

    devices = config.get(CONF_DEVICES, {})
    switches = []
    data = hass.data[DATA_ARPSPOOF]

    for object_id, device_config in devices.items():
        address = device_config.get(CONF_ADDRESS)
        friendly_name = device_config.get(CONF_FRIENDLY_NAME)
        type = -1

        if validators.ipv4(address):
            type = 0
        elif validators.mac_address(address):
            type = 1

        if type > -1:
            _LOGGER.debug("Adding '%s' as switch '%s'",
                          address, friendly_name)

            switches.append(
                ArpSpoofSwitch(
                    data,
                    object_id,
                    friendly_name,
                    address,
                    type,
                    device_config.get(CONF_ICON)
                )
            )
        else:
            _LOGGER.debug("Address '%s' is not valid IP or MAC", address)

    if not switches:
        _LOGGER.error("No devices added")
        return False

    add_devices(switches)


class ArpSpoofSwitch(SwitchDevice):
    """Representation of a ArpSpoof switch."""

    def __init__(self, instance, object_id, friendly_name, address,
                 address_type, icon):
        """Initialize the switch."""
        self._name = friendly_name
        self._address = address
        self._address_type = address_type
        self._state = False
        self._icon = icon
        self.entity_id = ENTITY_ID_FORMAT.format(object_id)
        self._instance = instance

        # _LOGGER.debug("Switch INIT")

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
        self._state = self._instance.add_device(self._address, self._address_type)
        self.schedule_update_ha_state()

    def turn_off(self):
        """Turn the entity off."""
        self._state = self._instance.remove_device(self._address, self._address_type)
        self.schedule_update_ha_state()
