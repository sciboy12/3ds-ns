#!/usr/bin/env python3
import asyncio
import re
import os
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
    #pass
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
    
    def extract_mac(device):
        device = device.replace("Device ", "")
        device = device.replace(" Nintendo Switch", "")
        mac = device.replace("\n", "")
        return mac
    
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
        device = device_list_new.replace(device_list_old, "")
        # Strip off extra to yield mac address
        device = extract_mac(device)

        print("Now paired to " + device)
        print("Enter a device name for this Switch, or press Ctrl+C to skip.")
        try:
            name = input(": ")
            config = configparser.ConfigParser(delimiters=('='))
            config['devices'] = {device: name}
            with open('/root/config.ini', 'r+') as configfile:
                config.read('/root/config.ini')
                config.write(configfile)
        except KeyboardInterrupt:
            pass
        
    
    async def unpair():
        clear()
        print("This function is not implemented yet.")
        print("Press Enter to continue..")
        input()
        return
        while True:
            choice = input()
            if int(choice) in range(0, device_count):
                mac = switch.extract_mac(device_list[int(choice)])
                break
            else:
                print("Invalid input.")
        out = subprocess.Popen(["bluetoothctl", device], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        config.read('/root/config.ini')

        config.remove_option("devices", mac)

        with open('/root/config.ini', 'w') as configfile:
                configfile.write("[devices]")

async def event_loop(mac):
    from evdev import ecodes, InputDevice, list_devices
    import re

    global controller_state

    controller_state.button_state.set_button('r_stick', True)    
    await asyncio.sleep(0.1)
    controller_state.button_state.set_button('r_stick', False)
        
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
            switch.extract_mac(device)
            # Append mac to list of switches
            device_list.append(device)

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
        choice_list = choice_list + str(device_count + 1) + ") " + name + "\n"
        device_count = device_count + 1
        
    while True:
        clear()
        choice = input("Please select a Switch:\n" + choice_list + " \
                       \np) Pair New \
                       \nu) Unpair Device\n\n: ")

        if str(choice) == 'p':
            await switch.pair()
            break
        elif str(choice) == 'u':
            await switch.unpair()
            await menu()
        
        elif int(choice) in range(0, device_count):

            mac = switch.extract_mac(device_list[int(choice)])
            clear()
            print("Scanning...")
            await switch.connect(mac)
            await event_loop(mac)
            #break
        else:
            print("Invalid input.")


##    #Pair new Switch
##    if choice == 'p' or 'P':
##        await switch.pair()
##    if choice == 'u' or 'U':
##        await switch.unpair()
##    else:
##        mac = switch.extract_mac(device_list[int(choice)])

    
##async def main():
##    #from evdev import ecodes, InputDevice, list_devices
##    #import re
####
####    config = configparser.ConfigParser(delimiters=('='))
####    config.read('/root/config.ini')
####    choice_list = ""
####    device_count = 0
####    if not Path("/root/config.ini").is_file():
####        config['devices'] = {}
####        subprocess.run(["touch", "/root/config.ini"])
####        
####        with open('/root/config.ini', 'w') as configfile:
####            configfile.write("[devices]")
####
####    menu()
####    for option in config.options("devices"):
####        name = config.get("devices", option)
####        choice_list = choice_list + str(device_count + 1) + ") " + name + "\n"
####        device_count = device_count + 1
##
####    while True:
####        choice = input("Please select a Switch:\n" + choice_list + " \
####                       \np) Pair New \
####                       \nu) Unpair Device\n\n: ")
####
####
####        if choice in ['p', 'u']:
####            clear()
####            break
####        elif int(choice) in range(0, device_count):
####                    clear()
####                    break
####        else:
####            print("Invalid Input.")
####
####    
####    #Pair new Switch
####    if choice == 'p' or 'P':
####        pair = True
####        pair_device()
####    elif choice == 'u' or 'U':
####        unpair = True
####    else:
####        mac = extract_mac(device_list[int(choice)])
##
##
##    #clear()
##    #print("\033c", end="")
####    
####    # Create memory containing default controller stick calibration
####    spi_flash = FlashMemory()
####
####    # the type of controller to create
####    controller = Controller.PRO_CONTROLLER # or JOYCON_L or JOYCON_R
####
####    # a callback to create the corresponding protocol once a connection is established
####    factory = controller_protocol_factory(controller, spi_flash=spi_flash)
##
##    # start the emulated controller
##    print("Scanning...")
##    if 'pair' in locals():
##        clear()
##        #print("\033c", end="")
##        # Get list of devices prior to pairing for later use
##        device_list_old = get_paired()
##        
##        print("Scanning...")
##        transport, protocol = await create_hid_server(factory)
##
##        # Get list again after pairing
##        device_list_new = get_paired()
##        # Remove old list from new to isolate device
##        device = device_list_new.replace(device_list_old, "")
##        # Strip off extra to yield mac address
##        device = extract_mac(device)
##
##        print("Now paired to " + device)
##        print("Enter a device name for this Switch, or press Ctrl+C to skip.")
##        try:
##            name = input(": ")
##            config = configparser.ConfigParser(delimiters=('='))
##            config['devices'] = {device: name}
##            with open('/root/config.ini', 'r+') as configfile:
##                config.read('/root/config.ini')
##                config.write(configfile)
##        except KeyboardInterrupt:
##            pass
##        
##    elif 'unpair' in locals():
##        print("Select a Switch to unpair\n")
##        choice = input(": ")
##        if int(choice) in range(0, device_count):
##              device = extract_mac(device_list[int(choice)])
##              unpair_device(device)
##              exit()
##    else:
##
##            
##        transport, protocol = await create_hid_server(factory, reconnect_bt_addr=mac)
##
##    #Get a reference to the state being emulated.
##    #global controller_state
##    controller_state = protocol.get_controller_state()
##    
##    clear()
    #print("\033c", end="")

    #Wait for input to be accepted
##    print("Connecting...")
##    await controller_state.connect()
##    clear()
##    #print("\033c", end="")
##
####    if 'pair' in locals():
####        print("Pairing successful. Please rerun this script to connect\n")
####        exit()
##
##    print("Connected.")

##    x_deadzone = 15
##    y_deadzone = 15
##    x_deadzone_inv = 2048 - x_deadzone
##    y_deadzone_inv = 2048 - y_deadzone
##    x_deadzone = 2048 + x_deadzone
##    y_deadzone = 2048 + y_deadzone
##    x_fine = 0
##    y_fine = 0
##    threshold = 78
##    value_new = 0
##    value_old = 0
##    event_loop()
##    controller_state.button_state.set_button('r_stick', True)
##    
##    await asyncio.sleep(0.1)
##    controller_state.button_state.set_button('r_stick', False)
####    global running
####    running = True
##        
##    devices = [InputDevice(path) for path in list_devices()]
##    for device in devices:
##            if bool(re.search('Nintendo 3DS', device.name)) == True:
##                ds = InputDevice(device.path)
##
##    #ds = InputDevice('/dev/input/event14')    
##    ds.grab()
##
####    lx_old = 0
####    lx_new = 0
####    ly_old = 0
####    ly_new = 0
##    
####    lx_status = 0
####    lx_range = [0, 4095]
####    home1 = False
####    home2 = False
####    home_on = False
##
##
##    btn_mapping = {
##               ecodes.BTN_EAST: 'a',
##               ecodes.BTN_SOUTH: 'b',
##               ecodes.BTN_NORTH: 'x',
##               ecodes.BTN_WEST: 'y',
##               ecodes.BTN_TL2: 'l',
##               ecodes.BTN_TR2: 'r',
##               ecodes.BTN_TL: 'zl',
##               ecodes.BTN_TR: 'zr',
##               ecodes.BTN_START: 'plus',
##               ecodes.BTN_SELECT: 'home',
##               ecodes.BTN_DPAD_UP: 'up',
##               ecodes.BTN_DPAD_DOWN: 'down',
##               ecodes.BTN_DPAD_LEFT: 'left',
##               ecodes.BTN_DPAD_RIGHT: 'right'
##               }
##
##    stick_mapping = {
##               ecodes.ABS_X: l_stick_state.set_h,
##               ecodes.ABS_Y: l_stick_state.set_v,
##               ecodes.ABS_RX: r_stick_state.set_h,
##               ecodes.ABS_RY: r_stick_state.set_v
##               }
##
##    async for event in ds.async_read_loop():
##        try:
##            if event.type == ecodes.EV_KEY:
##                if event.value == 1:
##                    if callable(btn_mapping[event.code]):
##                        btn_mapping[event.code]()
##                    else:
##                        controller_state.button_state.set_button(btn_mapping[event.code], True)
##                        
##                else:
##                    if callable(btn_mapping[event.code]):
##                        btn_mapping[event.code]()
##                        
##                    controller_state.button_state.set_button(btn_mapping[event.code], False)
##
##            elif event.type == ecodes.EV_ABS:
##                stick_mapping[event.code](event.value)
##                
##        except KeyError:
##            pass
        
try:
    
    # Elevate to root user if needed
    if os.getuid() != 0:
        elevate()
    devices = get_paired()
    #out = subprocess.Popen(["bluetoothctl", "paired-devices"], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    #devices = subprocess.run(["bluetoothctl", "paired-devices"])
    #devices = str(out.stdout.read())
    
    n_devices = devices.count('\\n')
    device_list = []
    name_list = []
    #out = subprocess.Popen(["bluetoothctl", "paired-devices"], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    for i in range(0, n_devices):
        
        device = str(out.stdout.readline().decode())
        if "Nintendo Switch" in device:
            # Strip off extra to yield mac address
            extract_mac(device)
            device_list.append(device)

##    else:
##        for i in range(0, len()):
##            devices = next(islice(f, line_number - 1, line_number))


##    if not 'pair' in locals():
##        while True:
##            #for i in range(0, n_devices):
##                #print(name_list[i])
##            choice = input("Please select a Switch:\
##                           \n1) sciguy's Switch\
##                           \n2) snote's Switch\
##                           \np) Pair New\
##                                      \n\n: ")
##            if choice in ['1', '2', 'p']:
##                clear()
##                #print("\033c", end="")
##                break
##            else:
##                print("Invalid Input.")
##
##        
##    #sciguy's Switch
##    if choice == '1':
##        mac = "D4:F0:57:64:39:64"
##    #snote's Switch
##    elif choice == '2':
##        mac = "48:A5:E7:73:02:E9"
##    #Pair new Switch
##    elif choice == 'p':
##        pair = True

##    running = True
    
    loop = asyncio.get_event_loop()
    loop.create_task(menu())
    loop.run_forever()
    exit()
    
except OSError as e:
    print(e)
    #print("Unable to connect. Exiting...")
    exit()
