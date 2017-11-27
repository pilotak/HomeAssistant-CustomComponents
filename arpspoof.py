import logging
import voluptuous as vol
import time

from homeassistant.config import load_yaml_config_file
import homeassistant.helpers.config_validation as cv
from datetime import timedelta
from homeassistant.helpers.event import track_time_interval
from homeassistant.const import (EVENT_HOMEASSISTANT_STOP, CONF_SCAN_INTERVAL)

from scapy.all import conf, send, ARP, arping, get_if_hwaddr, Ether

DOMAIN = "arpspoof"

_LOGGER = logging.getLogger(__name__)

CONF_INTERFACE = "interface"

ARPSPOOF_SCHEMA = vol.Schema({
    vol.Required(CONF_INTERFACE): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=30): cv.positive_int
})

# def timing(f):
#     def wrap(*args):
#         time1 = time.time()
#         ret = f(*args)
#         time2 = time.time()
#         _LOGGER.debug('%s function took %0.3f ms',
#                       f.__name__, (time2 - time1) * 1000.0)
#         return ret
#     return wrap


def setup(hass, config):
    conf = config[DOMAIN]
    interface = conf.get(CONF_INTERFACE)
    scan_interval = conf.get(CONF_SCAN_INTERVAL)

    if not scan_interval:
        scan_interval = 30

    hass.data[DOMAIN] = ArpSpoof(hass, interface)

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, hass.data[
                         DOMAIN].restore_all())

    def loop(event_time):
        hass.data[DOMAIN].loop()

    def online(event_time):
        hass.data[DOMAIN].is_online()

    track_time_interval(hass, loop, timedelta(seconds=2))
    track_time_interval(hass, online, timedelta(seconds=scan_interval))

    return True


class ArpSpoof(object):

    def __init__(self, hass, interface):
        """Init the api."""
        self._hass = hass
        self._interface = interface
        self._devices = []
        self._waiting_list = []
        self._arp_cache = []
        self._router_ip = self.get_default_gateway_ip(interface)
        self._router_mac = self.get_default_gateway_mac(interface)

        _LOGGER.debug("Router IP: %s MAC address: %s",
                      self._router_ip,
                      self._router_mac)

        self.update_cache()

    #@timing
    def update_cache(self):
        try:
            ans, unans = arping(self._router_ip + "/24",
                                iface=self._interface, verbose=False)

            self._arp_cache = []

            if ans:
                for s, r in ans:
                    self._arp_cache.append([r[ARP].psrc, r[Ether].src.lower()])

            _LOGGER.debug("ARP cache: %s", self._arp_cache)
        except Exception as e:
            _LOGGER.error("Error when trying update ARP cache: %s", str(e))

    def get_mac(self, victimIP):
        try:
            index = [i for i, x in enumerate(self._arp_cache) if x[0] == victimIP]

            if index:
                return self._arp_cache[index[0]][1]

        except:
            _LOGGER.error("Error when trying to get MAC of %s", victimIP)
        
        return None

    def get_ip(self, victimMAC):
        try:
            index = [i for i, x in enumerate(self._arp_cache) if x[1] == victimMAC.lower()]

            if index:
                return self._arp_cache[index[0]][0]

        except:
            _LOGGER.error("Error when trying to get IP of %s", victimMAC)
        
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
            return [x[2] for x in conf.route.routes if x[3] == interface and x[2] != '0.0.0.0'][0]
        except IndexError:
            _LOGGER.error(
                "Error: Network interface '%s' not found!", interface)
            return False

    def spoof(self, index):
        try:
            victimIP = self._devices[index][0]
            victimMAC = self._devices[index][1]

            send(ARP(op=2, pdst=victimIP, psrc=self._router_ip,
                     hwdst=victimMAC), iface=self._interface, verbose=False)
            send(ARP(op=2, pdst=self._router_ip, psrc=victimIP,
                     hwdst=self._router_mac), iface=self._interface, verbose=False)
        except:
            _LOGGER.error("Error when trying to spoof device IP: %s MAC: %s",
                     victimIP, victimMAC)

    def restore(self, index):
        try:
            victimIP = self._devices[index][0]
            victimMAC = self._devices[index][1]

            _LOGGER.info("Enabling internet for device IP: %s MAC: %s",
                         victimIP, victimMAC)

            del self._devices[index]

            send(ARP(op=2, pdst=victimIP, hwdst=victimMAC, psrc=self._router_ip,
                     hwsrc=self._router_mac), count=4, iface=self._interface, verbose=False)
            send(ARP(op=2, pdst=self._router_ip, hwdst=self._router_mac, psrc=victimIP,
                     hwsrc=victimMAC), count=4, iface=self._interface, verbose=False)

        except:
            _LOGGER.error("Error when restoring IP: %s", victimIP)

    def add_device(self, address, address_type):
        _LOGGER.debug(
            "Trying to disable internet for device address: %s", address)

        if address not in [j for i in self._devices for j in i]:
            if address_type == 0:  # IP based
                mac = self.get_mac(address)
                ip = address
            elif address_type == 1:  # MAC based
                mac = address
                ip = self.get_ip(address)

            if ip is not None and mac is not None:
                _LOGGER.info("Spoofing device IP: %s MAC: %s", ip, mac)

                self._devices.append([ip, mac])

                _LOGGER.debug("Device list now: %s", self._devices)
            else:
                _LOGGER.info(
                    "Device %s is not online, I will try again later", address)
                self._waiting_list.append([address, address_type])

                _LOGGER.debug("Waiting list now: %s", self._waiting_list)

            return True

        else:
            _LOGGER.warning("Device address: %s is already on list", address)

        return False

    def remove_device(self, address, address_type):
        _LOGGER.debug(
            "Trying to enable internet for device address: %s", address)

        index = [i for i, x in enumerate(self._devices) if x[address_type] == address]

        if index:
            self.restore(index[0])

        else:
            waiting_index = [i for i, x in enumerate(self._waiting_list) if x[0] == address]

            if waiting_index:
                del self._waiting_list[waiting_index[0]]

                _LOGGER.info("Device %s removed from waiting list", address)
            else:
                _LOGGER.error("Removing device %s from waiting list", address)

        _LOGGER.debug("Waiting list now: %s", self._waiting_list)
        _LOGGER.debug("Device list now: %s", self._devices)

        return False

    def is_online(self):
        self.update_cache()

        for i in range(len(self._waiting_list)):
            _LOGGER.debug("Trying device %s if it's online",
                          self._waiting_list[i][0])

            if self._waiting_list[i][1] == 0:  # IP
                mac = self.get_mac(self._waiting_list[i][0])

                if mac is not None:
                    _LOGGER.info(
                        "Device became online, spoofing IP: %s MAC: %s", self._waiting_list[i][0], mac)

                    self._devices.append([self._waiting_list[i][0], mac])
                    del self._waiting_list[i]

            elif self._waiting_list[i][1] == 1:  # MAC
                ip = self.get_ip(self._waiting_list[i][0])

                if ip is not None:
                    _LOGGER.info(
                        "Device became online, spoofing IP: %s MAC: %s", ip, self._waiting_list[i][0])

                    self._devices.append([ip, self._waiting_list[i][0]])
                    del self._waiting_list[i]

    def enable_packet_forwarding():
        with open(IP_FORWARD, 'w') as fd:
            fd.write('1')

    def disable_packet_forwarding():
        with open(IP_FORWARD, 'w') as fd:
            fd.write('0')

    def loop(self):
        for i in range(len(self._devices)):
            self.spoof(i)

    def restore_all(self):
        for i in range(len(self._devices)):
            self.restore(i)
