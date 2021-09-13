from os import name
from PIL import Image, ImageDraw
import time
import keyboard
from threading import Event
from Actors import *
import Utils
import math
from specialkey import nonprint_dict
import configparser
import appdirs

from thespian.actors import Actor, ActorSystem, ActorAddress, ActorExitRequest

import platform

if platform.system() == "Windows":
    import win32api
    import win32con

    g_user = win32api.GetUserNameEx(win32con.NameSamCompatible).replace("\\", "-")
else:
    g_user = Utils.darwin_get_username()

print(g_user)

class MouseData:
  def __init__(self, app, time, button, action, x, y):
      self.app = app
      self.elapsed_time = time
      self.button = button
      self.action = action
      self.x = x
      self.y = y

class KeyboardData:
    def __init__(self, app, key_name, event_type, time):
        self.app = app
        self.key_name = key_name
        self.event_type = event_type
        self.time = time


class KSApplication(Actor):
    def __init__(self):
        self.sequence = None
        self.actors = []
        self.stop_event = Event()
        self.user = g_user
        self.enabled = True
        self.dnaref = None
        self.keydatastore = None
        self.downKeys = {}
        self.filters = []
        self.active_app = "Terminal.app"
        self.username = ""
        self.machine_id = ""
        self.init_path = appdirs.user_data_dir("TruU Key and Mouse Data Collector", "TruU")

        if not os.path.exists(self.init_path):
            os.makedirs(self.init_path)

        if os.path.exists(self.init_path + '/filters.ini'): #
            #Load the config file to get the filtered apps
            cfg = configparser.ConfigParser()
            cfg.read(self.init_path + '/filters.ini') #

            if 'Filters' in cfg:
                if 'Apps' in cfg['Filters']:
                    apps = cfg['Filters']['Apps']
                    apps = list(map(lambda x: x.strip(),apps.split(',')))

                    for a in apps:
                        if a == '':
                            continue
                        self.filters.append(a)
        else:
            self.save_filters()


    def save_filters(self):
        cfg = configparser.ConfigParser()
        cfg['Filters'] = {'Apps':','.join(self.filters)}
        with open(self.init_path + '/filters.ini', 'w') as cfile: #
            cfg.write(cfile)

    def add_filter(self, app_name):
        if app_name in self.filters:
            return

        self.filters.append(app_name)

        for actor in self.actors:
            self.send(actor['aref'],{"add_filter_app":app_name})

        self.save_filters()

    def delete_filter(self, app_name):
        if app_name not in self.filters:
            return

        self.filters.remove(app_name)

        for actor in self.actors:
            self.send(actor['aref'],{"delete_filter_app":app_name})

        self.save_filters()

    def on_activate(self):
        self.enabled = not self.enabled
        if self.enabled:
            self.send(self.dnaref,
                {
                    "title": "KS Collector",
                    "text": "Collecting Enabled"
                })
        else:
            self.send(self.dnaref,
                {
                    "title": "KS Collector",
                    "text": "Collecting Paused"
                })


    def __generate_icon(self, color="green"):
        width = 200
        height = 200
        image = Image.new("RGB", (width, height), color="black")
        dc = ImageDraw.Draw(image)
        dc.rectangle((width // 2, 0, width, height // 2), fill=color)
        dc.rectangle((0, height // 2, width // 2, height), fill=color)
        return image


    def add_actor(self, actor_name):
        class_str = actor_name
        aref = None
        try:
            aref = self.createActor(eval(class_str), globalName = class_str)
        except NameError:
            try:
                class_str = "Actors.{}".format(class_str)
                aref = self.createActor(eval(class_str))
            except NameError:
                print("Error: Actor Class {} not found".format(actor_name))
                return

        self.send(aref,{"load": "{}_data".format(self.user)})
        for f in self.filters:
            self.send(aref,{"add_filter_app":f})
        adata = {'actor':class_str, 'aref':aref}
        self.actors.append(adata)


    def on_click_handler(self, elapsed_time, x, y, button, pressed):

        if not self.enabled:
            return

        #get output vars
        app = self.active_app
        button = str(button).split('.')[-1].capitalize()
        x = int(x)
        y = int(y)
        action = 'Pressed' if pressed else 'Released'
        # check if control key is pressed, if yes, change to right click
        ctrl_bool = ('ctrl' in self.downKeys) or ('ctrl_r' in self.downKeys)
        button = 'Button.right' if ctrl_bool else button
        button = str(button).split('.')[-1].capitalize()

        print(f'ctrl_bool:{ctrl_bool}')
        # construct output data
        md = MouseData(app, elapsed_time, button, action, x, y)

        for actor in self.actors:
            self.send(actor['aref'],{"mbe": md, "app": app})

    def on_move_handler(self, elapsed_time, x, y):
        """
        Listener for when mouse is moved.
        Returns x and y pixel locations
        """
        if not self.enabled:
            return

        #print("KSApp On Move Handler")
        #elapsed_time = time.perf_counter()
        app = self.active_app
        x = int(x)
        y = int(y)
        button = 'NoButton'
        action = 'Move'

        # construct output data
        md = MouseData(app, elapsed_time, button, action, x, y)

        # print(mbe_dict)
        for actor in self.actors:
            self.send(actor['aref'],{"mbe": md, "app": app})


    def on_scroll_handler(self, elapsed_time, x, y, dx, dy):

        """
        Listener for when a scroll event occurs.
        Location at scroll, how far it was scrolled.
        """

        if not self.enabled:
            return

        #elapsed_time = time.perf_counter()

        app = self.active_app
        x = int(x)
        y = int(y)

        left_right_direction = math.copysign(1, dx)

        if dy != 0:
            up_down_direction = math.copysign(1, dy)
            if up_down_direction == -1:
                up_down_direction = 'Up'
            elif up_down_direction == 1:
                up_down_direction = 'Down'
            else:
                up_down_direction = up_down_direction

            button = 'Scroll'
            action = up_down_direction
        else:
            button = 'Scroll'
            action = 'None'

        # construct output data
        md = MouseData(app, elapsed_time, button, action, x, y)

        # print(mbe_dict)
        for actor in self.actors:
            self.send(actor['aref'],{"mbe": md, "app": app})

    def __getKeyName(self, key):

        # special character does not have char in pynput package
        try:
            key_name = key.char
        except AttributeError:
            key_name = key.name
        # solve comma problam to prevent friction in parsing later
        if key_name == ',':
            key_name = 'comma'
        # solve functional key problem
        if key_name is not None:
            key_name = key_name.lower()
        else:
            key_name = 'special'

        # deal with special keys
        key_name = nonprint_dict[key_name] if key_name in nonprint_dict else key_name

        return key_name


    def on_press_handler(self, elapsed_time, key):
        # If we are not collecting then simply skip this event
        if not self.enabled:
            return
        app = self.active_app

        # event type - up or down
        event_type = "down"

        key_name = self.__getKeyName(key)

        # check downkey dict
        if key_name in self.downKeys:
            print("Held Key {}".format(key_name))
            return
        else:
            self.downKeys[key_name] = True

        # send to actor
        kd = KeyboardData(app, key_name, event_type, elapsed_time)
        for actor in self.actors:
            self.send(actor['aref'],{"kbe": kd, "app": app})


    def on_release_handler(self, elapsed_time, key):
        # If we are not collecting then simply skip this event
        if not self.enabled:
            return
        app = self.active_app

        # event type - up or down
        event_type = "up"

        #
        key_name = self.__getKeyName(key)

        # check downkey dict, delete if exists
        if key_name in self.downKeys:
            del self.downKeys[key_name]

        # send to actor
        kd = KeyboardData(app, key_name, event_type, elapsed_time)
        for actor in self.actors:
            self.send(actor['aref'],{"kbe": kd, "app": app})


    # def key_press_handler(self, event):
    #     # If we are not collecting then simply skip this event
    #     if not self.enabled:
    #         return
    #
    #     if event.event_type == "down":
    #         if event.scan_code in self.downKeys:
    #             print("Held Key {}".format(event.scan_code))
    #             return
    #         else:
    #             self.downKeys[event.scan_code] = True
    #
    #     if event.event_type == "up":
    #         if event.scan_code in self.downKeys:
    #             del self.downKeys[event.scan_code]
    #
    #     for actor in self.actors:
    #         self.send(actor['aref'],{"kbe": event,"app":self.active_app})

    def receiveMessage(self, message, sender):

        if isinstance(message, ActorExitRequest):
            print("Exit Request Recieved")

        if isinstance(message,dict):
            if 'start' in message:
                print("Starting Application...")
                self.run(None)

            if 'shutdown' in message:
                print("Stopping Application...")
                self.shutdown_app()

            if 'add_actor' in message:
                self.add_actor(message['add_actor'])

            # if 'kbe' in message:
            #     self.key_press_handler(message['kbe'])

            if 'ChangeEvent' in message:
                print(f"Changed to App {message['ChangeEvent']}")
                self.active_app = message['ChangeEvent']

            if 'keyboard_press_event' in message:
                kdata = message['keyboard_press_event']
                self.on_press_handler(**kdata)

            if 'keyboard_release_event' in message:
                kdata = message['keyboard_release_event']
                self.on_release_handler(**kdata)

            if 'mouse_click_event' in message:
                mdata = message['mouse_click_event']
                self.on_click_handler(**mdata)

            if 'mouse_move_event' in message:
                mdata = message['mouse_move_event']
                self.on_move_handler(**mdata)

            if 'mouse_scroll_event' in message:
                mdata = message['mouse_scroll_event']
                self.on_scroll_handler(**mdata)

            if 'add_filter' in message:
                self.add_filter(message['add_filter'])

            if 'delete_filter' in message:
                self.delete_filter(message['delete_filter'])

            if 'get_filters' in message:
                self.send(sender,self.filters)

            if 'get_active_app' in message:
                self.send(sender,self.active_app)

            if 'on_activate' in message:
                self.on_activate()

            if 'username' in message:
                self.username = message['username']

            if 'machine' in message:
                self.machine_id = message['machine']

            if 'get_username' in message:
                self.send(sender,self.username)

            if 'get_machine' in message:
                self.send(sender,self.machine_id)

            if 'save_buffers' in message:
                for actor in self.actors:
                    self.send(actor,{'save_buffers':True})
            
            if 'scoring_mode' in message:
                for actor in self.actors:
                    if actor['actor'] == 'FullKeyLogActor':
                        self.send(actor['aref'], message)

    def run(self, icon):
        self.dnaref = self.createActor(DisplayNotificationActorNew, globalName="DisplayNotification")
        self.keydatastore = self.createActor(KeyDataStoreActor, globalName="KeyDataStore")
        self.send(self.dnaref,{"title": "KS Collector", "text": "Collector Enabled"})

        print("Started!")

    def shutdown_app(self):
        self.enabled = False
        # Begin Clean Shutdown Procedure
        print("Shutting down...")
        self.send(self.dnaref,
            {"title": "KS Collector", "text": "Collector Shutting Down..."}
        )
        # Tell all the actors to save their current data
        for actor in self.actors:
            self.send(actor["aref"],{"save": "{}_data".format(self.user)})
        time.sleep(3)  # Time to allow actors to save
        for actor in self.actors:
            self.send(actor["aref"], ActorExitRequest())  # Shutdown all actor threads
        self.send(self.dnaref,ActorExitRequest())
        self.send(self.keydatastore,ActorExitRequest())

        print("Shutdown Complete...")

    def set_icon_sequence(self, image_list):
        self.sequence = image_list
