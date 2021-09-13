from typenet.data_v2 import mac_os_sample
from typenet.data_v2 import windows_driver_sample
from typenet.model_v2.transforms import typenet_features
from typenet.model_v2.typeNet import TypeNet
from typenet.scoring_model import platt_scoring
from pathlib import Path
import torch
import pandas as pd
import numpy as np

#from Collector import scoring_mode_off, scoring_mode_on

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from itertools import count

from thespian.actors import Actor
from keyboard import KeyboardEvent
from keyboard import _os_keyboard
import time

from thespian.actors import Actor, ActorSystem, ActorAddress, ActorExitRequest

# from KeyEventParser import TriGraphDataCollector, vkconvert
import Utils as u
import KeyEventParser
from KeyEventParser import vkconvert

# import Plotting.plot_funcs as pf
import os
import platform
import json
import requests

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
    else:
        os.system("""
            osascript -e 'display notification "{}" with title "{}"'
        """.format(text,title))

def checkUploadTime(cur_time, first_time, prev_time):
    key_seq_min = 1
    between_key_sec = 2
    key_seq_thresh = key_seq_min * 6e10
    between_key_thresh = between_key_sec * 1e9

    #print(f'Sequence total time: {cur_time - first_time}')
    #print(f'Time since last event: {cur_time - prev_time}')
    # check if timelapse since first key has been 2 mins
    if cur_time - first_time > key_seq_thresh:
        return True

    if cur_time - prev_time > between_key_thresh:
        return True

    return False

class KeyDataStoreActor(Actor):
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
            print(message)
            title = message["title"] if "title" in message else "Notification"
            text = message["text"] if "text" in message else ""
            icon_path = message["icon_path"] if "icon_path" in message else "N.ico"
            duration = message["duration"] if "duration" in message else 1
            _display_notification(title, text, icon_path, duration)


class DeepkeyActor(Actor):
    SEQ_LEN = 30
    TYPENET_FNAME = 'TypeNetModel_g500_u50_l20.pt'
    SCORING_MODEL_FNAME = 'scoring_model_chirag.json'

    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        if torch.cuda.is_available():
            self.device = torch.device('cuda')
        else:
            self.device = torch.device('cpu')
        
        self.scorer = None
        if Path(self.SCORING_MODEL_FNAME).exists():
            with open(self.SCORING_MODEL_FNAME, 'r') as f:
                json_string = f.read()
            self.scorer = platt_scoring.scorer_from_json(json_string)
        else:
            print(f'file {self.SCORING_MODEL_FNAME} not found')
        
        self.threshold = 0.6
        self.press_release_data = []
        self.pressed = {}
        self.scoring_mode = False
        
        # create blank file for scores, initiated once a key is pressed each
        #   time keymouselogger is restarted
        self.fpath = Path(__file__).parent.resolve()
        with open(self.fpath / 'scripts' / 'scores_out.txt', 'w') as f:
            f.write('')

    def receiveMessage(self, message, sender):
        if isinstance(message, dict):
            try:
                self.scoring_mode = message['scoring_mode']
            except KeyError:
                print("Dictionary has incorrect key")
            return

        fpath = Path(__file__).parent.resolve() / self.TYPENET_FNAME
        if not fpath.exists() or not self.scorer:
            print(f'Either file {self.TYPENET_FNAME} or {self.SCORING_MODEL_FNAME} not found')
            return
        
        if not self.scoring_mode:
            return

        app_name, key_name, event_type, time = message[0]
        
        if event_type == 'D':
            if key_name not in self.pressed:
                self.pressed[key_name] = (app_name, event_type, time)
        elif key_name in self.pressed:
            release_time = time
            press_time = self.pressed[key_name][2]
            self.press_release_data.append((key_name, press_time, release_time))
            del self.pressed[key_name]
        else:
            print(f"no press on code {(app_name, key_name, event_type, time)}")
    
        if len(self.press_release_data) < self.SEQ_LEN:
            return
        
        press_release_df = pd.DataFrame(self.press_release_data, columns=['keycode', 'PRESS_TIME', 'RELEASE_TIME'])
        for i in 'PRESS_TIME', 'RELEASE_TIME':
            press_release_df[i] = press_release_df[i].astype('float64')
            press_release_df[i] = pd.to_datetime(press_release_df[i], unit='ns').dt.tz_localize('UTC').dt.tz_convert('US/Mountain')
        coder = mac_os_sample.TruUKeyCoder(unknown_symbol="zero")
        press_release_df['keycode'] = coder.encode(press_release_df.keycode)
        
        timing_df = press_release_df
        assert not timing_df.isna().any(axis=None)
        timing_df = timing_df.astype('int64')
        # # data has nanosecond accuracy, div by 1e9 gives seconds, typenet_features() wants it in milliseconds though
        # # so div by 1e6 instead
        timing_df.loc[:, ['PRESS_TIME', 'RELEASE_TIME']] = timing_df.loc[:, ['PRESS_TIME', 'RELEASE_TIME']] / 1e6
        typenet_feat_df = pd.DataFrame(
            typenet_features(timing_df.values).T, columns=['keycode', 'hold', 'dd', 'ud', 'uu']
        )

        model = TypeNet(False, False, self.SEQ_LEN).to(self.device)
        model.load_state_dict(torch.load(fpath, map_location=self.device))
        model.eval()
        with torch.no_grad():
            X = torch.tensor(typenet_feat_df.values).unsqueeze(0).float().to(self.device)
            x_len = [self.SEQ_LEN,]
            embedding = model(X, x_len).cpu().numpy()

        prob = self.scorer.predict_proba(embedding)[:, 1]
        #self.temp = prob
        classification = 'imposter'
        if prob > self.threshold:
            classification = 'genuine'
        print(prob, classification)

        # write raw scores to a file
        with open(self.fpath / 'scripts' / 'scores_out.txt', 'a') as f:
            f.write(str(prob[0]) + '\n')

        self.press_release_data.clear()
        
class FullKeyLogActor(Actor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.key_data = []
        # self.name = "FKL"
        self.filter_apps = []
        self.ksaref = None
        self.filtered = False
        self.active_app = ""
        self.boot_time = time.time_ns()
        self.first_key_time = time.time_ns() # init the time of first key event in a sequence
        self.prev_key_time  = time.time_ns() # keep track of the prev key event time
        self.cur_time = time.time_ns()
        self.batch_num = 0
        self.key_data_for_deepkey = []
        
        self.deepkey_actor = None
        
        if platform.system() == "Windows":
            if 65 not in _os_keyboard.scan_code_to_vk:
                print("Setting up VK Tables")
                _os_keyboard.init()


    # def checkUploadTime(self):
    #     key_seq_min = 1
    #     between_key_sec = 2
    #     key_seq_thresh = key_seq_min * 6e10
    #     between_key_thresh = between_key_sec * 1e9
    #     print(f'Key Sequence last time: {self.cur_time - self.first_key_time}')
    #     print(f'Time since last key event: {self.cur_time - self.prev_key_time}')
    #     # check if timelapse since first key has been 2 mins
    #     if self.cur_time - self.first_key_time > key_seq_thresh:
    #         return True
    #
    #     if self.cur_time - self.prev_key_time > between_key_thresh:
    #         return True
    #
    #     return False

    def send_data(self):
        if len(self.key_data) > 0:
            kibanaActorKey = self.createActor(UploadKeytoKibana, globalName="UploadKeytoKibana")
            # kibana actors
            key_buffer = self.key_data.copy()
            self.send(kibanaActorKey, key_buffer)
            # after uploaded to kibana, clear key seq and reset first key time and prev key time
            self.key_data.clear()
            self.first_key_time = 0
            self.prev_key_time = 0
            self.batch_num += 1

    def send_to_deepkey(self, identifier, message={'scoring_mode':False}):
        if self.deepkey_actor is None:
            self.deepkey_actor = self.createActor(DeepkeyActor, globalName="DeepkeyActor")
        if identifier == 'scoring_identifier':
            self.send(self.deepkey_actor, message)
        elif identifier == 'key_buffer':
            #send to deepkey actor
            deepkey_buffer = self.key_data_for_deepkey.copy()
            #print(f"Sending to deepkey...{self.key_data_for_deepkey}")
            self.send(self.deepkey_actor, deepkey_buffer)
            #empty the buffer 
            self.key_data_for_deepkey.clear()
        else:
            print('HOW did I get here??')

    def receiveMessage(self, message, sender):
        if isinstance(message, dict):
            if "kbe" in message:
                #if message['app'] is not None:
                    #if message['app'] not in self.filter_apps:
                        #print(f"Keyboard: Filtered App [{message['app']}]")
                        #return
                e = message["kbe"]
                #get current time of the key event
                e.time = (e.time*pow(10,9))+self.boot_time # current even time for below events
                self.cur_time = e.time

                #print(f'key data length: {len(self.key_data)}')
                # set first key time and previous key event time
                if len(self.key_data) == 0:
                    self.first_key_time = self.cur_time
                    self.prev_key_time = self.cur_time
                else:
                    self.prev_key_time = float(self.key_data[-1][-1])

                #determine key pos
                if e.event_type == "up":
                    e.event_type = "U"
                elif e.event_type == "down":
                    e.event_type = "D"
                else:
                    return
                #print(f'current keyboard entry:{(e.app, e.key_name, e.event_type, str(e.time))}')
                # print(f'current mouse entry:{(e.app, str(e.elapsed_time), e.button, e.action, str(e.x), str(e.y))}')

                if message['app'] not in self.filter_apps:
                    empty = ""
                    print(f"Keyboard: Filtered App [{message['app']}]")
                    self.key_data.append((e.app, empty, e.event_type, str(e.time)))
                else:
                    self.key_data.append((e.app, e.key_name, e.event_type, str(e.time)))

                self.key_data_for_deepkey.append((e.app, e.key_name, e.event_type, str(e.time)))

                if len(self.key_data_for_deepkey) == 1:
                    self.send_to_deepkey('key_buffer')

                if checkUploadTime(self.cur_time, self.first_key_time, self.prev_key_time):
                    self.send_data()

            if 'add_filter_app' in message:
                appname = message['add_filter_app']
                print(f"Added Filter for app {appname}")
                self.filter_apps.append(appname)

            if 'delete_filter_app' in message:
                appname = message['delete_filter_app']
                print(f"Deleted Filter for app {appname}")
                self.filter_apps.remove(appname)

            if 'ksapp_ref' in message:
                self.ksaref = message['ksapp_ref']

            if 'save_buffers' in message:
                print("Saving Keyboard Buffers")
                self.send_data()
                #Close out the upload actor to force it to send it's buffers to the database -- it will be reopened on the next call to send_data
                #self.send(self.createActor(UploadKeytoKibana, globalName="UploadKeytoKibana"),ActorExitRequest())

            if 'get_batch_num' in message:
                self.send(sender, {"batch_num": self.batch_num})
            
            if 'scoring_mode' in message:
                self.send_to_deepkey('scoring_identifier', message)
               
        if isinstance(message, ActorExitRequest):
            print("Sending out Last Keyboard Data Buffers")
            self.send_data()


class UploadKeytoKibana(Actor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.batch = []
        print("Upload to Key Started")

    def receiveMessage(self, message, sender):

        if isinstance(message, ActorExitRequest):
            print("Finalizing Keyboard Uploads")
            if len(self.batch) > 0:
                print("Unsent batches...")
                for pb in self.batch:
                    u.upload_mouse(pb)
                self.batch.clear()
            return

        if not isinstance(message, list):
            print('not a list')
            return

        post_body = {
            'type': 'keyboard',
            'filename': u.get_file_name(event = 'keyboard'),
            'data': message
        }

        # batch upload
        self.batch.append(post_body)

        if len(self.batch) == 5:
            for pb in self.batch:
                u.upload_keyboard(pb)
            self.batch.clear()


        # json_buffer = json.dumps(message)
        # #r = requests.post(self.url, data = json_buffer)
        #
        # self.file_path = "/Users/ChiragSharma/Desktop/typeData.csv"
        # if not self.file_path.endswith('.csv'):
        #     file_path += '.csv'
        #
        # #Open the output file
        # print('Writing to file now...')
        # print(message)
        # print(self.file_path)
        # with open(self.file_path,'a') as f:
        #     for i in range(len(message)):
        #         kd = message[i]
        #         if kd is None:
        #             print("Skipping key due to none type...")
        #             continue
        #         f.writelines([",".join(kd) + "\n"])


class FullMouseLogActor(Actor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.mouse_data = []
        self.filter_apps = []
        self.ksaref = None
        self.filtered = False
        self.active_app = ""
        self.boot_time = time.time_ns()
        self.first_mouse_time = time.time_ns()
        self.prev_mouse_time = time.time_ns()
        self.cur_time = time.time_ns()
        self.batch_num = 0
        print("Booting Full Mouse Log Actor")

    def getActiveApp(self):
        return self.active_app

    def send_data(self):
        if len(self.mouse_data) > 0:
            kibanaActorMouse = self.createActor(UploadMousetoKibana, globalName="UploadMousetoKibana")
            mouse_buffer = self.mouse_data.copy()
            self.send(kibanaActorMouse, mouse_buffer)
            self.mouse_data.clear()
            self.first_mouse_time = 0
            self.prev_mouse_time = 0
            self.batch_num += 1

    def receiveMessage(self, message, sender):

        if isinstance(message, dict):
            if "mbe" in message:
                #if message['app'] is not None:
                    #if message['app'] not in self.filter_apps:
                        #print(f"Mouse: Filtered App [{message['app']}]")
                        #return
                e = message['mbe']

                # this works for recording elapsed time
                # self.cur_time = (e.elapsed_time*pow(10,9))+self.boot_time
                e.elapsed_time = (e.elapsed_time*pow(10,9))+self.boot_time
                self.cur_time = e.elapsed_time

                if len(self.mouse_data) == 0:
                    self.first_mouse_time = self.cur_time
                    self.prev_mouse_time = self.cur_time
                else:
                    self.prev_mouse_time = float(self.mouse_data[-1][1])
                    # prev_time_elapsed = float(self.mouse_data[-1][1])
                    # self.prev_mouse_time = (prev_time_elapsed*pow(10,9))+self.boot_time
                #print(f'current mouse entry:{(e.app, str(e.elapsed_time), e.button, e.action, str(e.x), str(e.y))}')
                self.mouse_data.append((e.app, str(e.elapsed_time), e.button, e.action, str(e.x), str(e.y)))

                if checkUploadTime(self.cur_time, self.first_mouse_time, self.prev_mouse_time):
                    self.send_data()

                #if message['app'] not in self.filter_apps:
                    #print(f"Mouse: Filtered App [{message['app']}]")

            if 'add_filter_app' in message:
                appname = message['add_filter_app']
                print(f"Added Filter for app {appname}")
                self.filter_apps.append(appname)

            if 'delete_filter_app' in message:
                appname = message['delete_filter_app']
                print(f"Deleted Filter for app {appname}")
                self.filter_apps.remove(appname)

            if 'save_buffers' in message:
                print("Saving Mouse Buffers")
                self.send_data()

            if 'get_batch_num' in message:
                self.send(sender, {"batch_num": self.batch_num})

        if isinstance(message, ActorExitRequest):
            print("Sending out Last Mouse Data Buffers")
            self.send_data()



class UploadMousetoKibana(Actor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.batch = []
        print("Upload to Mouse Started")

    def receiveMessage(self, message, sender):

        if isinstance(message, ActorExitRequest):
            print("Finalizing Mouse Uploads")
            if len(self.batch) > 0:
                print("Unsent batches...")
                for pb in self.batch:
                    u.upload_mouse(pb)
                self.batch.clear()
            return

        if not isinstance(message, list):
            print('not a list')
            return

        post_body = {
            'type': 'mouse',
            'filename': u.get_file_name(event = 'mouse'),
            'data': message
        }

        # batch upload
        self.batch.append(post_body)

        if len(self.batch) == 5:
            for pb in self.batch:
                u.upload_mouse(pb)
            self.batch.clear()


        # json_buffer = json.dumps(message)
        # #r = requests.post(self.url, data = json_buffer)
        #
        # if not self.file_path.endswith('.csv'):
        #     file_path += '.csv'
        #
        # #Open the output file
        # print('Writing to file now...')
        # print(message)
        # with open(self.file_path,'a') as f:
        #     for i in range(len(message)):
        #         kd = message[i]
        #         if kd is None:
        #             print("Skipping mouse due to none type...")
        #             continue
        #         f.writelines([",".join(kd) + "\n"])



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
