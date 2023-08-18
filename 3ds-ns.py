#!/usr/bin/env python3
import asyncio
import re
import sys, os

if os.getuid() != 0:
    print("Please run as root.")
    exit(126)
    
# Change into the directory containing this file
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

from numpy import interp
from pygame import time
import nxbt

class l_stick_state:
    def set_h(packet, value):
        value = int(interp(value, [-156, 156], [-100, 100]))
        packet["L_STICK"]["X_VALUE"] = value
        return packet

    def set_v(packet, value):
        value = int(interp(value, [-156, 156], [100, -100]))
        packet["L_STICK"]["Y_VALUE"] = value
        return packet
    
class r_stick_state:
    def set_h(packet, value):
        value = int(interp(value, [-94, 94], [-100, 100]))
        packet["R_STICK"]["X_VALUE"] = value
        return packet
    
    def set_v(packet, value):
        value = int(interp(value, [-94, 94], [100, -100]))
        packet["R_STICK"]["Y_VALUE"] = value
        return packet

async def connect():
    controller_index = nx.create_controller(nxbt.PRO_CONTROLLER,
                                            reconnect_address=nx.get_switch_addresses())
    
    print("Scanning...")
    nx.wait_for_connection(controller_index)

    print("Connected.")
    return controller_index

# Handles forwarding of events
async def event_loop(controller_index):
    from evdev import ecodes, InputDevice, list_devices
    import re
    
    # Get reference to 3DS evdev device
    devices = [InputDevice(path) for path in list_devices()]
    for device in devices:
            if bool(re.search('Nintendo 3DS', device.name)) == True:
                ds = InputDevice(device.path)
    ds.grab()

    btn_mapping = {
               ecodes.BTN_EAST: 'A',
               ecodes.BTN_SOUTH: 'B',
               ecodes.BTN_NORTH: 'X',
               ecodes.BTN_WEST: 'Y',
               ecodes.BTN_TL2: 'L',
               ecodes.BTN_TR2: 'R',
               ecodes.BTN_TL: 'ZL',
               ecodes.BTN_TR: 'ZR',
               ecodes.BTN_START: 'PLUS',
               ecodes.BTN_SELECT: 'MINUS',
               ecodes.BTN_DPAD_UP: 'DPAD_UP',
               ecodes.BTN_DPAD_DOWN: 'DPAD_DOWN',
               ecodes.BTN_DPAD_LEFT: 'DPAD_LEFT',
               ecodes.BTN_DPAD_RIGHT: 'DPAD_RIGHT'
               }

    stick_mapping = {
               ecodes.ABS_X: l_stick_state.set_h,
               ecodes.ABS_Y: l_stick_state.set_v,
               ecodes.ABS_RX: r_stick_state.set_h,
               ecodes.ABS_RY: r_stick_state.set_v
               }
    
    # Init PyGame clock
    clock = time.Clock()
    
    # Containins current button/stick states
    from nxbt.nxbt import DIRECT_INPUT_PACKET
    packet = DIRECT_INPUT_PACKET

    # Main loop
    async for event in ds.async_read_loop():
        try:
            # Set the corresponding value in the packet to the
            # contents of the key referenced by the button pressed
            if event.type == ecodes.EV_KEY:
                packet[btn_mapping[event.code]] = bool(event.value)
            elif event.type == ecodes.EV_ABS:
                packet = stick_mapping[event.code](packet, event.value)
            
        except KeyError:
            pass
        
        # Press Home if L and Start are pressed
        if packet["ZL"] and packet["PLUS"] == True:
            packet["HOME"] = True
        else:
            packet["HOME"] = False
            
        # Press Capture if R and Start are pressed
        if packet["ZR"] and packet["PLUS"] == True:
            packet["CAPTURE"] = True
        else:
            packet["CAPTURE"] = False

        # Send packet to Switch
        nx.set_controller_input(controller_index, packet)

        # Limit input rate to 240Hz
        clock.tick(240)
        
async def main():
    controller_index = await connect()
    await event_loop(controller_index)

# Init NXBT
nx = nxbt.Nxbt()

try:    
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
    
except KeyboardInterrupt:
    print("Exiting...")
    exit()
