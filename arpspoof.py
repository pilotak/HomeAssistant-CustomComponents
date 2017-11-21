import logging
import voluptuous as vol

from homeassistant.config import load_yaml_config_file
import homeassistant.helpers.config_validation as cv
from datetime import timedelta
from homeassistant.helpers.event import track_time_interval
from homeassistant.const import (EVENT_HOMEASSISTANT_STOP)

from scapy.all import*

DOMAIN = "arpspoof"

_LOGGER = logging.getLogger(__name__)

CONF_INTERFACE = "interface"

ARPSPOOF_SCHEMA = vol.Schema({
    vol.Required(CONF_INTERFACE): cv.string
})


def setup(hass, config):
    conf = config[DOMAIN]
    interface = conf.get(CONF_INTERFACE)

    _LOGGER.debug("Interface specified: %s", interface)

    hass.data[DOMAIN] = ArpSpoof(hass, interface)

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, hass.data[
                         DOMAIN].restore_all())

    def loop(event_time):
        hass.data[DOMAIN].loop()

    track_time_interval(hass, loop, timedelta(seconds=2))

    return True


class ArpSpoof(object):

    def __init__(self, hass, interface):
        """Init the api."""
        self._hass = hass
        self._interface = interface
        self._devices = [[], []]
        self._router_ip = self.get_default_gateway_ip(interface)
        self._router_mac = self.get_default_gateway_mac(interface)

        _LOGGER.debug("Router IP: %s MAC address: %s",
                      self._router_ip,
                      self._router_mac)

    def mac_snag(self, victimIP):
        try:
            ans, unans = arping(
                victimIP + "/24", iface=self._interface, verbose=False)

            if ans:
                for s, r in ans:
                    return r[Ether].src
            else:
                return None

        except:
            _LOGGER.error("Error when trying to get MAC of %s", victimIP)
            return None

    def get_default_gateway_mac(self, interface):
        try:
            return get_if_hwaddr(interface)
        except OSError as e:
            _LOGGER.error(
                "Error when trying to get MAC of router on interface '%s': %s",
                e.args[1])

        return None

    def get_default_gateway_ip(self, interface):
        try:
            return [x[2] for x in scapy.all.conf.route.routes if x[3] == interface and x[2] != '0.0.0.0'][0]
        except IndexError:
            _LOGGER.error(
                "Error: Network interface '%s' not found!", interface)
            return False

    def spoof(self, victimIP, victimMAC):
        _LOGGER.debug("Spoofing IP: %s MAC: %s", victimIP, victimMAC)

        try:
            send(ARP(op=2, pdst=victimIP, psrc=self._router_ip,
                     hwdst=victimMAC), iface=self._interface, verbose=False)
            send(ARP(op=2, pdst=self._router_ip, psrc=victimIP,
                     hwdst=self._router_mac), iface=self._interface, verbose=False)
        except:
            _LOGGER.error("Error when trying to spoof IP: %s",
                          self._devices[0][i])

    def restore(self, victimIP, victimMAC):
        _LOGGER.info("Enabling internet for device IP: %s MAC: %s",
                     victimIP, victimMAC)

        try:
            self._devices[0].remove(victimIP)
            self._devices[1].remove(victimMAC)

            send(ARP(op=2, pdst=victimIP, hwdst=victimMAC, psrc=self._router_ip,
                     hwsrc=self._router_mac), count=4, iface=self._interface, verbose=False)
            send(ARP(op=2, pdst=self._router_ip, hwdst=self._router_mac, psrc=victimIP,
                     hwsrc=victimMAC), count=4, iface=self._interface, verbose=False)
        except:
            _LOGGER.error("Error when restoring IP: %s", victimIP)

    def add_device(self, ip):
        _LOGGER.debug("Trying to disable internet for device IP: %s", ip)

        if ip not in self._devices[0]:
            mac = self.mac_snag(ip)

            if mac is not None:
                _LOGGER.info("Adding device IP: %s MAC: %s", ip, mac)

                self._devices[0].append(ip)
                self._devices[1].append(mac)

                # _LOGGER.debug("Device IP array now: %s", self._devices[0])

                return True

            else:
                _LOGGER.warning(
                    "Failed spoofing device IP: %s, could not get MAC address",
                    ip)
        else:
            _LOGGER.warning("Device IP: %s is already on list", ip)

        return False

    def remove_device(self, ip):
        _LOGGER.debug("Trying to enable internet for device IP: %s", ip)

        if ip in self._devices[0]:
            index = self._devices[0].index(ip)

            self.restore(ip, self._devices[1][index])

            # _LOGGER.debug("Device IP array now: %s", self._devices[0])

            return False
        else:
            _LOGGER.warning("Device IP: %s is not on list", ip)

        return True

    def enable_packet_forwarding():
        with open(IP_FORWARD, 'w') as fd:
            fd.write('1')

    def disable_packet_forwarding():
        with open(IP_FORWARD, 'w') as fd:
            fd.write('0')

    def loop(self):
        for i in range(len(self._devices[0])):
            self.spoof(self._devices[0][i], self._devices[1][i])

    def restore_all(self):
        for i in range(len(self._devices[0])):
            self.restore(self._devices[0][i], self._devices[1][i])
