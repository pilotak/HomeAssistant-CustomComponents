---
layout: page
title: "Arpspoof"
description: "Instructions how to interact with ArpSpoof via Home Assistant on Raspberry Pi"
date: 2017-11-11 18:40
sidebar: true
comments: false
sharing: true
footer: true
ha_category: Automation
logo: 
ha_release: ---
ha_iot_class: "Local Push"
---
#WORK IN PROGRESS

The `arpspoof` component provides services that allow disabling specified devices internet in your network. Useful to control how much time the children spend on the internet.

## {% linkable_title Arpspoof Setup %}

*  Login to Raspberry Pi 

```bash
$ ssh pi@your_raspberry_pi_ip
```

### {% linkable_title Scapy %}

[scapy for Python3](https://github.com/phaethon/scapy) must be installed for this component to work. Follow the installation instructions for your environment, provided at the link. `scapy` installs Python 3 bindings by default as a system Python module. If you are running Home Assistant in a [Python virtual environment](/getting-started/installation-virtualenv/), make sure it can access the system module, by either symlinking it or using the `--system-site-packages` flag.

```bash
$ sudo apt-get install tcpdump
$ sudo pip3 install scapy-python3
```

We then we grant priviliges to run `scapy` as non-root.
```bash
$ sudo groupadd arp
$ sudo usermod -a -G arp homeassistant
$ newgrp homeassistant
$ sudo chgrp arp $(eval readlink -f `which python3`)
$ sudo setcap cap_net_raw,cap_net_admin+eip $(eval readlink -f `which python3`)
```

#### {% linkable_title Symlinking into virtual environment %}

Create a symlink to the `scapy` installation. Keep in mind different installation methods will result in different locations of cec.
 
```bash
$ ln -s /path/to/your/installation/of/scapy-python3 /path/to/your/venv/lib/python3.5/site-packages
```
##### {% linkable_title Symlinking examples: %}

For the default virtual environment of a [HASSbian Image for Raspberry Pi](/getting-started/installation-raspberry-pi-image/) the command would be as follows.

```bash
$ sudo ln -s /usr/local/lib/python3.5/dist-packages/scapy /srv/homeassistant/lib/python3.5/site-packages
```

For the default virtual environment of a [Raspberry Pi All-In-One installation](/getting-started/installation-raspberry-pi-all-in-one/) the command would be as follows.

```bash
$ sudo ln -s /usr/local/lib/python3.5/site-packages/scapy /srv/homeassistant/homeassistant_venv/lib/python3.5/site-packages
```

For the default virtual environment of a [Manual installation](/getting-started/installation-raspberry-pi/) the command would be as follows.

```bash
$ sudo ln -s /usr/local/lib/python3.5/site-packages/scapy /srv/hass/hass_venv/lib/python3.5/site-packages
```


<p class='note'>Only HASSbian image installation is verified, but all should work
</p>

## {% linkable_title Get interface name %}
You need to know trhough which interface you connected to your network so type in:
```bash
$ ip link show
```

This will show all interfaces available it can be ie. `eth0` or `wlan0` or `enx*****` but instead of asterisks there will be your MAC address or any other option. You will use this to specify interface, please see below.

## {% linkable_title Configuration example %}

In the following example, a Pi B+ running Home Assistant is connected to local network by Ethernet cable through `eth0` interface. All you need to know is the IP address of the device you want to disable internet (ie. child).

```yaml
# optional
logger:
 default: warning
 logs:
    scapy.runtime: error

arpspoof:
  interface: eth0

switch:
  - platform: arpspoof
    devices:
      test:
        friendly_name: my name
        ip_address: 192.168.1.105
        icon: 'mdi:laptop'
```


