#!/usr/bin/env python3
#import pygame
#from pygame.locals import *
import asyncio
import janus
import select
import re
from aioconsole import ainput
import threading, time
from numpy import interp
from joycontrol.protocol import controller_protocol_factory
from joycontrol.server import create_hid_server
from joycontrol.controller import Controller
from joycontrol.memory import FlashMemory

def video():
    #time.sleep(6)
    global event, mouseEvents, buttonEvents, keyEvents


    width = 1600
    height = 900
    #windowed 720p mode, for debugging purposes
    screen = pygame.display.set_mode((width, height), NOFRAME)
    
    pygame.display.init()
    info = pygame.display.Info()
    #os.environ['SDL_VIDEO_CENTERED'] = '1'


    # Basic opengl configuration
    glViewport(0, 0, info.current_w, info.current_h)
    glDepthRange(0, 1)
    glMatrixMode(GL_PROJECTION)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glShadeModel(GL_SMOOTH)
    glClearColor(0.0, 0.0, 0.0, 0.0)
    glClearDepth(1.0)
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    glDepthFunc(GL_LEQUAL)
    glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
    glEnable(GL_BLEND)
    global texID
    texID = glGenTextures(1)
    glClear(GL_COLOR_BUFFER_BIT)
    glLoadIdentity()
    glDisable(GL_LIGHTING)
    glEnable(GL_TEXTURE_2D)

    # Set PyGame to borderless fullscreen
    #pygame.display.set_mode((info.current_w, info.current_h), NOFRAME)
    pygame.display.init()
    pygame.fastevent.init()

    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    cap = cv2.VideoCapture(0)
    #cap = cv2.VideoCapture('/dev/video2')

    # Capture resolution
    cap_width = 720
    cap_height = 480

    # Capture resolution
    #width = 1280
    #height = 720

    # Capture FPS
    cap_fps = 60
    # Init PyGame clock 
    #fpsClock = pygame.time.Clock()

    #Set capture resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cap_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cap_height)
    # Set capture FPS
    cap.set(cv2.CAP_PROP_FPS, cap_fps)
    # Set capture buffer size
    #cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    cap.set(cv2.CAP_PROP_FOURCC, fourcc)
    
    frame_width  = cap.get(3)  # Returns float
    frame_height = cap.get(4)  # Returns float




    while True:

        #asyncio.run_coroutine_threadsafe(keys.put(event), loop)
        ret, frame = cap.read()

        frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        
        frame = cvimage_to_pygame(frame)
        frame = pygame.transform.scale(frame, (width, height))
        screen.blit(frame,(0,0))
##        texture = pygame.image.fromstring(frame.tobytes(), (int(frame_width), int(frame_height)), 'RGB')
##
##        surfaceToTexture( texture )
##        glBindTexture(GL_TEXTURE_2D, texID)
##        glBegin(GL_QUADS)
##        glTexCoord2f(0, 0); glVertex2f(-1, 1)
##        glTexCoord2f(0, 1); glVertex2f(-1, -1)
##        glTexCoord2f(1, 1); glVertex2f(1, -1)
##        glTexCoord2f(1, 0); glVertex2f(1, 1)
##        glEnd()
        pygame.display.flip()
        #fpsClock.tick(fps)

        for event in pygame.event.get():
            pass
        #event = pygame.event.get()
        mouseEvents.sync_q.put(pygame.mouse.get_rel())
        buttonEvents.sync_q.put(pygame.mouse.get_pressed())
        keyEvents.sync_q.put(pygame.key.get_pressed())
        #r_stick = pygame.mouse.get_rel()
        #keys = pygame.key.get_pressed()
            #keys.put(event)
            #if event.type == pygame.MOUSEMOTION:
                
        #print(event)
        #events.sync_q.put(event)          

def cvimage_to_pygame(image):
    """Convert cvimage into a pygame image"""
    return pygame.image.frombuffer(image.tobytes(), image.shape[1::-1],
                                   "RGB")

async def helper(dev):
     async for ev in dev.async_read_loop():
         print(repr(ev))

class l_stick_state:
    def set_h(value):
        #value = int(value * 13.128 + 2048)
        value = int(interp(value, [-156, 156], [0, 4095]))
        controller_state.l_stick_state.set_h(value)

        
    def set_v(value):
        #value = int(-value * 13.128 + 2048)
        value = int(interp(value, [-156, 156], [4095, 0]))
        controller_state.l_stick_state.set_v(value)

class r_stick_state:
    def set_h(value):
        #value = int(value * 13.128 + 2048)
        value = int(interp(value, [-156, 156], [0, 4095]))
        controller_state.r_stick_state.set_h(value)
    
    def set_v(value):
        #value = int(-value * 13.128 + 2048)
        value = int(interp(value, [-156, 156], [4095, 0]))
        controller_state.r_stick_state.set_v(value)

async def main():
    from evdev import ecodes, InputDevice, list_devices
    from elevate import elevate
    import os
    import re

    global pair
    global buttons
    global l_stick, r_stick
    global l_stickx
    #Clear screen
    print("\033c", end="")
    
    # Create memory containing default controller stick calibration
    spi_flash = FlashMemory()
    # the type of controller to create
    controller = Controller.PRO_CONTROLLER # or JOYCON_L or JOYCON_R
    # a callback to create the corresponding protocol once a connection is established
    factory = controller_protocol_factory(controller, spi_flash=spi_flash)
    # start the emulated controller
    print("Please Wait...")
    if 'pair' in locals():
        #Elevate to root user if needed
        if os.getuid() != 0:
            elevate()

        transport, protocol = await create_hid_server(factory)
        print("\033c", end="")
        print("Searching...")
    else:
        transport, protocol = await create_hid_server(factory, reconnect_bt_addr=mac)

    #Get a reference to the state being emulated.
    global controller_state
    controller_state = protocol.get_controller_state()
    print("\033c", end="")
    #Wait for input to be accepted
    print("Connecting...")
    await controller_state.connect()
    #Wait for input to be sent at least once
    #await controller_state.send()

    print("\033c", end="")
    if 'pair' in locals():
        print("Pairing successful. Please rerun this script to connect\n")
        exit()

    print("Connected.")

    x_deadzone = 15#305
    y_deadzone = 15#305
    x_deadzone_inv = 2048 - x_deadzone
    y_deadzone_inv = 2048 - y_deadzone
    x_deadzone = 2048 + x_deadzone
    y_deadzone = 2048 + y_deadzone
    x_fine = 0
    y_fine = 0
    threshold = 78
    value_new = 0
    value_old = 0
    #sensitivity = 325

    controller_state.button_state.set_button('r_stick', True)
    #await controller_state.send()
    await asyncio.sleep(0.1)
    controller_state.button_state.set_button('r_stick', False)
    global running
    running = True
        
    devices = [InputDevice(path) for path in list_devices()]
    for device in devices:
            if bool(re.search('Nintendo 3DS', device.name)) == True:
                ds = InputDevice(device.path)
            #if bool(re.search('keyboard', device.name)) == True:
            #       keyboard = ev.InputDevice(device.path)

    #ds = InputDevice('/dev/input/event14')    
    ds.grab()

    lx_old = 0
    lx_new = 0
    ly_old = 0
    ly_new = 0
    
    lx_status = 0
    lx_range = [0, 4095]
    home1 = False
    home2 = False
    home_on = False


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
        
try:

    while True:
        choice = input("Please select a Switch:\
                       \n1) sciguy's Switch\
                       \n2) snote's Switch\
                       \np) Pair New\
                                  \n\n: ")
        if choice in ['1', '2', 'p']:
            print("\033c", end="")
            break

        
    #sciguy's Switch
    if choice == '1':
        mac = "D4:F0:57:64:39:64"
    #snote's Switch
    elif choice == '2':
        mac = "48:A5:E7:73:02:E9"
    #Pair new Switch
    elif choice == 'p':
        global pair
        pair = True

    running = True
    
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
    exit()
    
except OSError as e:
    print(e)
    #print("Unable to connect. Exiting...")
    exit()
