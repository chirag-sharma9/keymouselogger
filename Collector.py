import sys
from PIL import Image, ImageDraw
from Actors import *
from Application import KSApplication, KeyboardData
from thespian.actors import ActorSystem
from multiprocessing import freeze_support
import setproctitle
import thespian
# from thespian.system import multiprocTCPBase, multiprocUDPBase, ActorAddress
# from thespian.system.multiprocTCPBase import TCPTransport
# import keyboard
import pynput.mouse as mouse
import pynput.keyboard as keyboard
import time
import pystray
from threading import Event

from Actors import FullKeyLogActor

import argparse

from AppKit import *
from Foundation import *
import Utils


#This is the global stop_event that we will set when we recieve an indicating that the app should quit
stop_event = Event()
pause_event = Event() #Global pause event used to pause the system during sleep and wake
keyboard_listener = None #Ref to keyboard listener
mouse_listener = None #Ref to mouse listener
enabled_flag = True #Enabled flag
asys = None #Global ActorSystem Object

def on_activate_click(icon):
    global enabled_flag
    print(enabled_flag)
    enabled_flag = not enabled_flag #Toggle the enabled state
    #Get the reference to the KSApp Actor
    aref = ActorSystem().createActor(KSApplication,globalName="KSApp")
    ActorSystem().tell(aref,{"on_activate":True})

def on_quit(icon):
    ActorSystem().tell(
        ActorSystem().createActor(KSApplication, globalName="KSApp"),
        {"shutdown":True}
    )
    icon.icon = generate_icon("red")
    stop_event.set()

def on_add_filtered_app(icon):
    if platform.system() == "Darwin":
        app_name = os.path.basename(Utils.darwin_select_file_action('/System/Applications','Select').strip().strip('/'))
        print(f"Adding {app_name} to list of filtered apps")
    else:
        print("Unsupported on this platform currently")
        return

    ActorSystem().tell(
        ActorSystem().createActor(KSApplication,globalName='KSApp'),
        {"add_filter":app_name}
    )

def on_delete_filtered_app(icon):
    if platform.system() == "Darwin":
        app_name = os.path.basename(Utils.darwin_select_file_action('/System/Applications','Select').strip().strip('/'))
        print(f"Deleing {app_name} from list of filtered apps")
    else:
        print("Unsupported on this platform currently")
        return

    ActorSystem().tell(
        ActorSystem().createActor(KSApplication,globalName='KSApp'),
        {"delete_filter":app_name}
    )

def get_monitored_apps():

    res = ActorSystem().ask(
        ActorSystem().createActor(KSApplication, globalName="KSApp"),
        {"get_filters":True}
    )
    return 'Monitored apps: ' + ', '.join([x.split('.')[0] for x in res])

def get_key_batch_nums():

    res = ActorSystem().ask(
        ActorSystem().createActor(FullKeyLogActor, globalName="FullKeyLogActor"),
        {"get_batch_num":True}
    )

    return "Key batch uploaded: " + str(res['batch_num'])

def get_mouse_batch_nums():

    res = ActorSystem().ask(
        ActorSystem().createActor(FullMouseLogActor, globalName="FullMouseLogActor"),
        {"get_batch_num":True}
    )

    return "Mouse batch uploaded: " + str(res['batch_num'])

def on_check_filtered():
    aref = ActorSystem().createActor(KSApplication, globalName="KSApp")

    filters = ActorSystem().ask(
        aref,
        {"get_filters":True}
    )
    active_app = ActorSystem().ask(
        aref,
        {"get_active_app":True}
        )
    #getActiveApp()
    active_app_name = active_app.split('.')[0]
    if active_app not in filters:
        return 'Current app: ' + active_app_name + " " + "[Filtered]"
    else:
        return 'Current app: ' + active_app_name + " " + "[Monitoring]"

def on_whitelist_current_app():
    aref = ActorSystem().createActor(KSApplication, globalName="KSApp")

    active_app = ActorSystem().ask(
        aref,
        {"get_active_app":True}
        )

    ActorSystem().tell(
        aref,
        {"add_filter":active_app}
    )

def on_blacklist_current_app():
    aref = ActorSystem().createActor(KSApplication, globalName="KSApp")

    active_app = ActorSystem().ask(
        aref,
        {"get_active_app":True}
        )

    ActorSystem().tell(
        aref,
        {"delete_filter":active_app}
    )

def privacy_policy():
    print()

def scoring_mode_on():
    aref = ActorSystem().createActor(KSApplication, globalName="KSApp")    
    
    ActorSystem().tell(
        aref,
        {"scoring_mode":True}
    )

    print('Scoring mode has been turned on')

def scoring_mode_off():
    aref = ActorSystem().createActor(KSApplication, globalName="KSApp")    
    
    ActorSystem().tell(
        aref,
        {"scoring_mode":False}
    )

    print('Scoring mode has been turned off')
   
def get_user_machine_info():
    return Utils.darwin_get_username() + "/" + Utils.darwin_get_machine_serial_number()

def __update_menu():
    if pause_event.isSet() or stop_event.isSet():
        return

    if enabled_flag:
        icon.icon = generate_icon('green')
    else:
        icon.icon = generate_icon('blue')

    # dynamically reset the dropdown menu (current app)
    icon.menu = pystray.Menu(
                pystray.MenuItem(
                    get_user_machine_info(),
                    lambda x: None,
                ),
                pystray.MenuItem(
                    "Enabled",
                    on_activate_click,
                    #default=True,
                    checked=lambda item: enabled_flag,
                ),
                pystray.MenuItem(
                    get_key_batch_nums(),
                    lambda x: None,
                ),
                pystray.MenuItem(
                    get_mouse_batch_nums(),
                    lambda x: None,
                ),
                pystray.MenuItem(
                    on_check_filtered(),
                    lambda x: None,
                ),
                pystray.MenuItem(
                    get_monitored_apps(),
                    lambda x: None,
                ),
                pystray.MenuItem(
                    "Allow Current App",
                    on_whitelist_current_app,
                    lambda x: None,
                ),
                pystray.MenuItem(
                    "Block Current App",
                    on_blacklist_current_app,
                    lambda x: None,
                ),
                pystray.MenuItem(
                    "Add Allowed App",
                    on_add_filtered_app,
                ),
                pystray.MenuItem(
                    "Remove Allowed App",
                    on_delete_filtered_app,
                ),
                pystray.MenuItem(
                    "Privacy Policy: If you block an application, what you type is private, but the mouse and keystroke timing data is collected",
                    privacy_policy,
                ),
                pystray.MenuItem(
                    "Turn Scoring Mode On",
                    scoring_mode_on,
                ),
                pystray.MenuItem(
                    "Turn Scoring Mode Off",
                    scoring_mode_off,
                ),
                pystray.MenuItem("Quit", on_quit))

    icon.update_menu()

def generate_icon(color="green"):
    width = 200
    height = 200
    image = Image.new("RGB", (width, height), color="black")
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color)
    dc.rectangle((0, height // 2, width // 2, height), fill=color)
    return image

def on_blah(icon):
    print('blah')

def runLoop(icon):
    icon.icon = generate_icon('green')
    icon.visible = True
    if platform.system() == "Darwin":
        #from PyObjCTools import AppHelper
        #AppHelper.runConsoleEventLoop()
        while not stop_event.isSet():
            if pause_event.isSet():
                print("Paused")
                time.sleep(1)#Just idle while we are sleeping...
                continue
            __update_menu()
            time.sleep(0.1)
    else:
        while not stop_event.isSet():
            time.sleep(0.1)

    try:
        print("Shutdown Actor System")
        time.sleep(5)
        asys.shutdown()
    except:
        print("Exception Caught During Shutdown")

    print("Stopping Application Icon")
    icon.stop()


#The Global Tray Icon Object
icon = pystray.Icon(
    "KSCollector",
    menu=pystray.Menu(
        pystray.MenuItem(
            "Enabled",
            on_activate_click,
            #default=True,
            checked=lambda item: enabled_flag,
        ),
        pystray.MenuItem(
            on_check_filtered(),
            lambda x: None,
        ),
        pystray.MenuItem(
            get_monitored_apps(),
            lambda x: None,
        ),
        pystray.MenuItem(
            "Add Filtered App",
            on_add_filtered_app,
        ),
        pystray.MenuItem(
            "Delete Filtered App",
            on_delete_filtered_app,
        ),
        pystray.MenuItem("Quit", on_quit),
    ),
)


class NotificationHandler(NSObject):
    """
    Class that handles the mount notifications
    """

    def handleChangeApp_(self, aNotification):
        print("blarg")

        #Don't attempt to tell the actor anything in the event that we are paused or stopping.
        if stop_event.isSet() or pause_event.isSet():
            return

        # Find the path to the just inserted volume
        url = aNotification.userInfo()["NSWorkspaceApplicationKey"].bundleURL()
        ActorSystem().tell(
            ActorSystem().createActor(KSApplication, globalName="KSApp"),
            {"ChangeEvent":os.path.basename(url.path())}
        )

    def handleSleep_(self, aNotification):
        print("Computer Sleep Request")
        pause_event.set()
        ActorSystem().tell(
            ActorSystem().createActor(KSApplication, globalName="KSApp"),
            {"save_buffers":True}
        )
        time.sleep(5)
        #mouse_listener.stop()
        #keyboard_listener.stop()
        #Shutdown the actor system
        ActorSystem().tell(
            ActorSystem().createActor(KSApplication,globalName="KSApp"),
            {"shutdown":True}
        )
        ActorSystem().shutdown()
        return

    def handleWake_(self, aNotification):
        print("Computer Wake Request")
        asys = ActorSystem('multiprocQueueBase')

        #Restart the actor system
        #Setup the main application actor that handles dispatching of all the events
        ksappref = ActorSystem().createActor(KSApplication,globalName="KSApp")
        # initiate keyboard collector
        ActorSystem().tell(ksappref,{"add_actor":"FullKeyLogActor"})
        # initiate mouse collector
        ActorSystem().tell(ksappref,{"add_actor":"FullMouseLogActor"})

        # mouse_listener = mouse.Listener(
        #     on_move=on_move_handler,
        #     on_click=on_click_handler,
        #     on_scroll=on_scroll_handler
        #     )

        # keyboard_listener = keyboard.Listener(
        #     on_press = on_press_handler,
        #     on_release = on_release_handler
        # )
        # #Restart the listeners
        #keyboard_listener.start()
        #time.sleep(2)
        #mouse_listener.start()
        # ActorSystem().tell(ksappref,{"username":Utils.darwin_get_username()})
        ActorSystem().tell(ksappref,{"machine":Utils.darwin_get_machine_serial_number()})
        ActorSystem().tell(ksappref,{"start":True})
        pause_event.clear()
        return



def key_press_handler(event):
    # This really should be done in the base keyboard library instead of here... but I didn't want to modify the base
    # library so instead I simply set the key time event here... if it turns out there is too much jitter in the results
    # we can change the base library so that the perf_counter call is closer to the actual OS keystroke event. However given that this runs as a
    # separate actor that only collects the data it shouldn't be too bad.
    event.time = time.perf_counter()
    ActorSystem().tell(
        ActorSystem().createActor(KSApplication,globalName="KSApp"),
        {"kbe":event}
    )
    #APPOBJ.key_press_handler(event)

def on_press_handler(key):

    elapsed_time = time.perf_counter()
    ActorSystem().tell(
        ActorSystem().createActor(KSApplication,globalName="KSApp"),
        {"keyboard_press_event": {
            'key': key,
            'elapsed_time': elapsed_time
        }}
    )

def on_release_handler(key):

    elapsed_time = time.perf_counter()

    ActorSystem().tell(
        ActorSystem().createActor(KSApplication,globalName="KSApp"),
        {"keyboard_release_event": {
            'key': key,
            'elapsed_time': elapsed_time
        }}
    )

def on_click_handler(x, y, button, pressed):
    elapsed_time = time.perf_counter()
    ActorSystem().tell(
        ActorSystem().createActor(KSApplication,globalName="KSApp"),
        {"mouse_click_event":{
            "x":x,
            "y":y,
            "button":button,
            "pressed":pressed,
            "elapsed_time":elapsed_time
        }}
    )

def on_move_handler(x, y):
    #print("Move Handlers")
    elapsed_time = time.perf_counter()
    ActorSystem().tell(
        ActorSystem().createActor(KSApplication,globalName="KSApp"),
        {"mouse_move_event":{
            "x":x,
            "y":y,
            "elapsed_time":elapsed_time
        }}
    )

def on_scroll_handler(x, y, dx, dy):
    elapsed_time = time.perf_counter()
    ActorSystem().tell(
        ActorSystem().createActor(KSApplication,globalName="KSApp"),
        {"mouse_scroll_event":{
            "x":x,
            "y":y,
            "dx":dx,
            "dy":dy,
            "elapsed_time":elapsed_time
        }}
    )

if __name__ == "__main__":
    freeze_support()
    print("loading app")
    asys = ActorSystem('multiprocQueueBase')

    #Setup the main application actor that handles dispatching of all the events
    ksappref = ActorSystem().createActor(KSApplication,globalName="KSApp")

    if platform.system() == "Darwin":
        #Subscribe to app change notifications, and sleep/wake events
        workspace = NSWorkspace.sharedWorkspace()
        notificationCenter = workspace.notificationCenter()
        notificationHandler = NotificationHandler.new()
        notificationCenter.addObserver_selector_name_object_(
            notificationHandler,
            "handleChangeApp:",
            NSWorkspaceDidActivateApplicationNotification,
            None,
        )
        notificationCenter.addObserver_selector_name_object_(
            notificationHandler,
            "handleSleep:",
            NSWorkspaceWillSleepNotification,
            None,
        )
        notificationCenter.addObserver_selector_name_object_(
            notificationHandler,
            "handleWake:",
            NSWorkspaceDidWakeNotification,
            None,
        )
    else:
        print("Warning!: Cannot Filter Apps on this Platform yet!")

    #Add in the Key and Mouse Log Actors
    # initiate keyboard collector
    ActorSystem().tell(ksappref,{"add_actor":"FullKeyLogActor"})
    # initiate mouse collector
    ActorSystem().tell(ksappref,{"add_actor":"FullMouseLogActor"})

    mouse_listener = mouse.Listener(
        on_move=on_move_handler,
        on_click=on_click_handler,
        on_scroll=on_scroll_handler
        )

    keyboard_listener = keyboard.Listener(
        on_press = on_press_handler,
        on_release = on_release_handler
    )

    #start the collectors and run the app
    # keyboard.hook(key_press_handler)
    keyboard_listener.start()
    time.sleep(2)
    mouse_listener.start()

    ActorSystem().tell(ksappref,{"username":Utils.darwin_get_username()})
    ActorSystem().tell(ksappref,{"machine":Utils.darwin_get_machine_serial_number()})
    ActorSystem().tell(ksappref,{"start":True})
    icon.run(runLoop)

    print("Stopping Listeners")
    #shut down the app and collectors when task is done
    keyboard_listener.stop()
    mouse_listener.stop()
    # keyboard.unhook(key_press_handler)
