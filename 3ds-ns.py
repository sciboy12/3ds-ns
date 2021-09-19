#!/usr/bin/env python3
import asyncio
import re
import sys, os
import configparser
from pathlib import Path
import threading, time
from numpy import interp
from itertools import islice
from elevate import elevate
import subprocess
from joycontrol.protocol import controller_protocol_factory
from joycontrol.server import create_hid_server
from joycontrol.controller import Controller
from joycontrol.memory import FlashMemory

def clear():
    pass
    subprocess.run(["clear"])

def get_paired():
    out = subprocess.Popen(["bluetoothctl", "paired-devices"], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    devices = str(out.stdout.read().decode())
    return devices

class l_stick_state:
    def set_h(value):
        value = int(interp(value, [-156, 156], [0, 4095]))
        controller_state.l_stick_state.set_h(value)

    def set_v(value):
        value = int(interp(value, [-156, 156], [4095, 0]))
        controller_state.l_stick_state.set_v(value)

class r_stick_state:
    def set_h(value):
        value = int(interp(value, [-156, 156], [0, 4095]))
        controller_state.r_stick_state.set_h(value)
    
    def set_v(value):
        value = int(interp(value, [-156, 156], [4095, 0]))
        controller_state.r_stick_state.set_v(value)

class switch:
    # Strips Bluetooth entry down to MAC Address
    def strip_mac(device):
        device = device.replace("Device ", "")
        device = device.replace(" Nintendo Switch", "")
        mac = device.replace("\n", "")
        return mac
    
    # Connects to specified MAC Address
    async def connect(mac):
                
        # Create memory containing default controller stick calibration
        spi_flash = FlashMemory()

        # the type of controller to create
        controller = Controller.PRO_CONTROLLER # or JOYCON_L or JOYCON_R

        # a callback to create the corresponding protocol once a connection is established
        factory = controller_protocol_factory(controller, spi_flash=spi_flash)
        
        if 'mac' in locals():
            # Connect to a previously paired Switch
            transport, protocol = await create_hid_server(factory, reconnect_bt_addr=mac)
        else:
            # Initiate pairing
            transport, protocol = await create_hid_server(factory)

        global controller_state
        controller_state = protocol.get_controller_state()

        clear()
        print("Connecting...")
        await controller_state.connect()

        clear()
        print("Connected.")
        print("Note that entering the Change Grip/Order screen will crash this program.")
        
    # Pairs computer to Switch
    async def pair():
                        
        # Create memory containing default controller stick calibration
        spi_flash = FlashMemory()

        # the type of controller to create
        controller = Controller.PRO_CONTROLLER # or JOYCON_L or JOYCON_R

        # a callback to create the corresponding protocol once a connection is established
        factory = controller_protocol_factory(controller, spi_flash=spi_flash)
        
        # Get list of devices prior to pairing for later use
        device_list_old = get_paired()
        
        print("Scanning...")
        transport, protocol = await create_hid_server(factory)

        # Get list again after pairing
        device_list_new = get_paired()
        # Remove old list from new to isolate device
        device = device_list_new.replace(device_list_old, '')
        # Strip off extra to yield mac address
        device = strip_mac(device)

        print("Now paired to " + device)
        print("Enter a username to represent this Switch, or press Ctrl+C if already paired previously.")
        try:
            name = input(": ")
            config = configparser.ConfigParser(delimiters=('='))
            config['devices'] = {device: name}
            with open('/root/config.ini', 'r+') as configfile:
                config.read('/root/config.ini')
                config.write(configfile)
        except KeyboardInterrupt:
            pass
        
    # Unpairs computer from Switch (WIP)
    async def unpair():
        clear()
        print("This function is not implemented yet.")
        print("Press Enter to continue..")
        input()
        return
        while True:
            choice = input()
            if int(choice) in range(0, device_count):
                mac = switch.strip_mac(device_list[int(choice)])
                break
            else:
                print("Invalid input.")
        out = subprocess.Popen(["bluetoothctl", device], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        config.read('/root/config.ini')

        config.remove_option("devices", mac)

        with open('/root/config.ini', 'w') as configfile:
                configfile.write("[devices]")

# Handles forwarding of events
async def event_loop(mac):
    from evdev import ecodes, InputDevice, list_devices
    import re

    global controller_state

    # Get reference to 3DS evdev device
    devices = [InputDevice(path) for path in list_devices()]
    for device in devices:
            if bool(re.search('Nintendo 3DS', device.name)) == True:
                ds = InputDevice(device.path)
    ds.grab()

    btn_mapping = {
               ecodes.BTN_EAST: 'a',
               ecodes.BTN_SOUTH: 'b',
               ecodes.BTN_NORTH: 'x',
               ecodes.BTN_WEST: 'y',
               ecodes.BTN_TL2: 'l',
               ecodes.BTN_TR2: 'r',
               ecodes.BTN_TL: 'zl',
               ecodes.BTN_TR: 'zr',
               ecodes.BTN_START: 'plus',
               ecodes.BTN_SELECT: 'home',
               ecodes.BTN_DPAD_UP: 'up',
               ecodes.BTN_DPAD_DOWN: 'down',
               ecodes.BTN_DPAD_LEFT: 'left',
               ecodes.BTN_DPAD_RIGHT: 'right'
               }

    stick_mapping = {
               ecodes.ABS_X: l_stick_state.set_h,
               ecodes.ABS_Y: l_stick_state.set_v,
               ecodes.ABS_RX: r_stick_state.set_h,
               ecodes.ABS_RY: r_stick_state.set_v
               }

    async for event in ds.async_read_loop():
        try:
            if event.type == ecodes.EV_KEY:
                if event.value == 1:
                    if callable(btn_mapping[event.code]):
                        btn_mapping[event.code]()
                    else:
                        controller_state.button_state.set_button(btn_mapping[event.code], True)
                        
                else:
                    if callable(btn_mapping[event.code]):
                        btn_mapping[event.code]()
                        
                    controller_state.button_state.set_button(btn_mapping[event.code], False)

            elif event.type == ecodes.EV_ABS:
                stick_mapping[event.code](event.value)
                
        except KeyError:
            pass

# Main menu
async def menu():
    devices = get_paired()
    n_devices = devices.count('\n')
    device_list = []
    name_list = []
    out = subprocess.Popen(["bluetoothctl", "paired-devices"], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    for i in range(0, n_devices):    
        device = str(out.stdout.readline().decode())
        if "Nintendo Switch" in device:
            # Strip off extra to yield mac address
            switch.strip_mac(device)
            # Append mac to list of switches
            device_list.insert(0, device)

    config = configparser.ConfigParser(delimiters=('='))
    config.read('/root/config.ini')
    choice_list = ""
    device_count = 0
    
    # Create config.ini if it does not exist
    if not Path("/root/config.ini").is_file():
        config['devices'] = {}
        subprocess.run(["touch", "/root/config.ini"])
        
        with open('/root/config.ini', 'w') as configfile:
            configfile.write("[devices]")

    # Generate text for prompt
    for option in config.options("devices"):
        name = config.get("devices", option)
        choice_list = choice_list + str(device_count + 1) + ") " + name

        # Append "'s" only when needed
        if not name[-1] == 's':
            choice_list = choice_list + "'s Switch\n"
        else:
             choice_list = choice_list + " Switch\n"

        device_count = device_count + 1
    while True:
        clear()
        choice = input("Please select a Switch:\n" + choice_list + " \
                       \np) Pair New \
                       \nu) Unpair Device \
                       \nq) Exit\n: ")

        if str(choice) == 'p':
            await switch.pair()
            break
        elif str(choice) == 'u':
            await switch.unpair()
            await menu()
        elif str(choice) == 'q':
            print("Exiting...")
            sys.exit()
        elif int(choice) in range(1, device_count + 1):
            print(device_count)
            mac = switch.strip_mac(device_list[int(choice) - 1])
            clear()
            print("Scanning...")
            await switch.connect(mac)
            await event_loop(mac)
        else:
            print("Invalid input.")
            
# Elevate to root user if needed
if os.getuid() != 0:
    elevate()
try:    
    loop = asyncio.get_event_loop()
    loop.create_task(menu())
    loop.run_forever()
    
except KeyboardInterrupt:
    print("Exiting...")
    exit()
