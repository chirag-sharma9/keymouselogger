from thespian.actors import Actor
from keyboard import KeyboardEvent
from keyboard import _os_keyboard
import time

from thespian.actors import Actor, ActorSystem, ActorAddress, ActorExitRequest

# from KeyEventParser import TriGraphDataCollector, vkconvert
import KeyEventParser
from KeyEventParser import vkconvert

# import Plotting.plot_funcs as pf
import os
import platform

# Platform Specific Configurations
if platform.system() == "Windows":
    print(_os_keyboard.scan_code_to_vk.keys())
    if platform.win32_ver()[0] == "10":
        import win10toast

        toaster = win10toast.ToastNotifier()
    else:
        toaster = None
else:
    toaster = None

if platform.system() == "Darwin":
    from AppKit import NSWorkspace

def _display_notification(title, text, icon_path=None, duration=3):
    if toaster is not None:
        toaster.show_toast(
            title, text, icon_path=icon_path, threaded=True, duration=duration
        )


class DataStoreActor(Actor):
    def __init__(self):
        super().__init__()
        self.db = {}

    def receiveMessage(self, msg, sender):
        if isinstance(msg, dict):
            if 'set' in msg:
                kv = msg['set']
                for k, v in kv.items():
                    self.db[k] = v
            if 'get' in msg:
                key = msg['get']
                if key in self.db:
                    self.send(sender, self.db[key])
                else:
                    self.send(sender, None)


class DisplayNotificationActorNew(Actor):
    def receiveMessage(self, message, sender):
        if isinstance(message, dict):
            title = message["title"] if "title" in message else "Notification"
            text = message["text"] if "text" in message else ""
            icon_path = message["icon_path"] if "icon_path" in message else "N.ico"
            duration = message["duration"] if "duration" in message else 1
            _display_notification(title, text, icon_path, duration)

class FullKeyLogActor(Actor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.key_data = []
        self.name = "FKL"
        self.filter_apps = []
        self.ksaref = None
        self.filtered = False
        self.active_app = ""
        self.boot_time = time.time_ns()
        if platform.system() == "Windows":
            if 65 not in _os_keyboard.scan_code_to_vk:
                print("Setting up VK Tables")
                _os_keyboard.init()

    def getActiveApp():
        return self.active_app

    def receiveMessage(self, message, sender):
        if isinstance(message, dict):
            if "kbe" in message:
                if message['app'] is not None:
                    if message['app'] in self.filter_apps:
                        print(f"Filtered App [{message['app']}]")
                        return
                e = message["kbe"]
                e.time = (e.time*pow(10,9))+self.boot_time # current even time for below events
                if e.event_type == "up":
                    e.event_type = "U"
                elif e.event_type == "down":
                    e.event_type = "D"
                else:
                    print("Unknown event")
                    return
                if e.scan_code < 0:
                    # This happens e.g. when in a remote desktop session... for some reason it sends a -255 scan code
                    # My guess is it is to notify the hook that it is losing ownership...?
                    return
                    # print(e.name, _os_keyboard.scan_code_to_vk[e.scan_code], e.event_type)
              #  self.key_collector.add_event(
              #      _os_keyboard.scan_code_to_vk[e.scan_code], e.event_type, e.time
              #  )

                if platform.system() == "Windows":
                        vk_code = _os_keyboard.scan_code_to_vk[e.scan_code]
                        key_name = (_os_keyboard.official_virtual_keys[vk_code])[0] if vk_code in _os_keyboard.official_virtual_keys else ''

                        #Fix the comma logging issue
                        if key_name == ',':
                            key_name = 'comma'

                        print(e.scan_code, key_name, e.event_type, e.time)
                        self.key_data.append((str(e.scan_code),key_name, e.event_type, str(e.time)))
                elif platform.system() == "Darwin":
                        print("[{}] {} {} {} {}".format(message['app'], e.scan_code,_os_keyboard.name_from_scancode(e.scan_code),e.event_type, e.time))
                        key_name = _os_keyboard.name_from_scancode(e.scan_code)

                        #Fix comma issue
                        if key_name == ',':
                            key_name = 'comma'

                        self.key_data.append((str(e.scan_code),key_name,e.event_type, str(e.time)))
                else:
                        print(e.scan_code, e.event_type, e.time)
                        self.key_data.append((e.scan_code, e.event_type, e.time))

            if "save" in message:
                file_path = message["save"]
                if not file_path.endswith('.csv'):
                    file_path += '.csv'
                file_path = "{}_{}".format(self.name,file_path)
                #Open the output file
                with open(file_path,'a') as f:
                    for i in range(len(self.key_data)):
                        kd = self.key_data[i]
                        if kd is None:
                            print("Skipping key due to none type...")
                            continue
                        f.writelines([",".join(kd) + "\n"])
                self.key_data.clear()

            if 'filter_app' in message:
                appname = message['filter_app']
                print(f"Added Filter for app {appname}")
                self.ksaref = sender
                self.filter_apps.append(appname)


            if 'ksapp_ref' in message:
                self.ksaref = message['ksapp_ref']


class AssignSessionActor(Actor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.key_data = []
        self.name = "FKL"
        self.filter_apps = []
        self.ksaref = None
        self.filtered = False
        self.active_app = ""
        self.boot_time = time.time_ns()

# class TriGraphHoldTimeActorNew(Actor):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.key_collector = KeyEventParser.TriGraphDataCollector()
#         self.name = "TGHT"
#         self.configured = False
#         self.ksaref = None
#         if 65 not in _os_keyboard.scan_code_to_vk:
#             print("Setting up VK Tables")
#             _os_keyboard.init()
#
#     def receiveMessage(self, message, sender):
#         if isinstance(message, dict):
#             if "kbe" in message:
#                 e = message["kbe"]
#                 if e.event_type == "up":
#                     e.event_type = "U"
#                 elif e.event_type == "down":
#                     e.event_type = "D"
#                 else:
#                     print("Unknown event")
#                     return
#                 if e.scan_code < 0:
#                     # This happens e.g. when in a remote desktop session... for some reason it sends a -255 scan code
#                     # My guess is it is to notify the hook that it is losing ownership...?
#                     return
#                     # print(e.name, _os_keyboard.scan_code_to_vk[e.scan_code], e.event_type)
#                 self.key_collector.add_event(
#                     _os_keyboard.scan_code_to_vk[e.scan_code], e.event_type, e.time
#                 )
#
#             # if 'plt' in message:
#             #    pf.plot_tri_matrix(self.key_collector.holdkey_matrix,vkconvert)
#
#             if "save" in message:
#                 file_path = message["save"]
#                 if not file_path.endswith(".npy"):
#                     file_path += ".npy"
#                 file_path = "{}_{}".format(self.name, file_path)
#                 cos = False
#                 if "clear_on_save" in message:
#                     cos = message["clear_on_save"]
#                 self.key_collector.save_state(file_path, cos)
#
#             if "load" in message:
#                 file_path = message["load"]
#                 file_path = "{}_{}".format(self.name, file_path)
#                 print("Attemping to load {}".format(file_path))
#                 if os.path.exists(file_path):
#                     self.key_collector.load_state(file_path)
#                 self.configured = True
#
#             if "stats" in message:
#                 self.key_collector.print_stats()
#
#             if 'ksapp_ref' in message:
#                 self.ksaref = message['ksapp_ref']
