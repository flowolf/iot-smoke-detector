# This script connects to WIFI and sends a message via MQTT.
#
# Copyright (C) 2018 Florian Klien 2018 <flowolf@klienux.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

import machine
import network
import socket
import ubinascii
import time
from umqtt.robust import MQTTClient



debug = True
NETWORK_CONNECT_TIMEOUT = 60 #seconds
INTERVAL = 10
DEV_ID = "SmokeDetector-{0}".format(ubinascii.hexlify(machine.unique_id()).decode('utf-8'))
MY_NETS = {
            #"your_net": "password",
          }

mqtt_server = "192.168.1.1"
topic = "/home/smoke/livingroom"

mqtt_user = "MQTTuser"
mqtt_pw = "MQTTpassword"

read_power = True

led = machine.Pin(2,machine.Pin.OUT)
led.value(0)

start_time = time.ticks_ms()

wlan = network.WLAN(network.STA_IF)
def do_connect():
    print("getting network")
    network_connect_start_time = time.ticks_ms()
    import network

    if not wlan.active():
        wlan.active(True)
    nets = wlan.scan()
    for net in nets:
        net = net[0].decode('utf-8')
        if net in MY_NETS and not wlan.isconnected():
            print('connecting to network: {}'.format(net))
            wlan.connect(net, MY_NETS[net])#, timeout=5000)
            while not wlan.isconnected():
                if debug:
                    led.value(1) # off
                if wlan.status() == network.STAT_IDLE:
                    print("ERROR: nothing going on")
                    break
                # if wlan.status() == network.STAT_CONNECTING:
                #     print("INFO: connecting to network")
                if wlan.status() == network.STAT_GOT_IP:
                    print("INFO: what are you doing here, shouldn't be here...")
                if wlan.status() == network.STAT_WRONG_PASSWORD or\
                    wlan.status() == network.STAT_NO_AP_FOUND or\
                    wlan.status() == network.STAT_CONNECT_FAIL:

                    print("ERROR: wifi has issues ({})".format(wlan.status()))
                    break
                if (network_connect_start_time + NETWORK_CONNECT_TIMEOUT*1000) < time.ticks_ms():
                    print("ERROR: network timeout. trying other network, or sleeping")
                    break
                machine.idle()
    if debug:
        led.value(0) # on
    print('network config:', wlan.ifconfig())

def mean(numbers):
    return float(sum(numbers)) / max(len(numbers), 1)

c = MQTTClient(DEV_ID, mqtt_server, user=mqtt_user, password=mqtt_pw)
#ap.active(False)
adc = machine.ADC(0)
# run notification forever, notify every INTERVAL seconds
while True:
    current_time = time.ticks_ms()
    do_connect()
    print("sending smoke alarm to MQTT")
    led.value(0)
    if read_power:
        power_vals = []
        voltage = 0
        for i in range(0,100):
            time.sleep_ms(1)
            power_vals.append(adc.read())
        voltage = mean(power_vals)*3.3*3/1024 # voltage of battery
        # less than 7 V is dangerous...
    try:
        c.connect()
        print("publishing: ")
        if read_power:
            print("power: {} V".format(voltage))
            c.publish(topic + "/voltage", str(voltage), retain=True)
            read_power = False # only read power at startup
        c.publish(topic, "smoke")
        c.disconnect()
    except:
        print("ERROR: connecting or sending data to MQTT server!")
    led.value(1)
    time.sleep(INTERVAL)
