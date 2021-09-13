# import numpy as np
from numpy import save as npsave
from numpy import load as npload
from numpy import array as nparray
import keyboard
import os


class KeyHoldDistribution(object):
    def __init__(self, key, prior, post):
        self.key = key
        self.prior = prior
        self.post = post
        self.timings = []

    def add_timing(self, timing):
        self.timings.append(timing)

    def add_timing_list(self, timinglist):
        self.timings.extend(timinglist)

    def get_times_ms(self):
        """
            Returns the timing vector in ms
        """
        return list(1000 * np.array(self.timings))

    def get_times_sec(self):
        return self.timings

    def __add__(self, other):
        # We want to combine two KeyHoldDistributions
        # We will only combine them if they are for the same key set
        assert not ((self.key != other.key) | (self.prior != other.prior) | (
                self.post != other.post)), "Key Distributions must be for the same key sets to be combined!"

        newdist = KeyHoldDistribution(self.key, self.prior, self.post)
        newdist.add_timing_list(self.timings)
        newdist.add_timing_list(other.timings)
        return newdist

    def __eq__(self, other):
        if ((self.key != other.key) | (self.prior != other.prior) | (self.post != other.post)):
            return False
        if len(self.timings) != len(other.timings):
            return False
        return (sorted(self.timings) == sorted(other.timings))


class BufferEventElement(object):
    def __init__(self, key, action, time):
        self.key = key
        self.action = action
        self.time = time
        self.delete = False


class VKKeyCode2KeyStoreKeyCode(object):
    def __init__(self):
        # alpha keys
        alphabet_dict = {k: v for (v, k) in enumerate(range(65, 91))}
        alphabet_lookup = {k: v for (v, k) in enumerate([chr(i) for i in range(65, 91)])}
        # Numeric Keys
        numeric_dict = {k: (v + len(alphabet_dict)) for (v, k) in enumerate(range(48, 58))}
        numeric_lookup = {str(k): (v + len(alphabet_lookup)) for (v, k) in enumerate(range(0, 10))}
        # Combine the two dictionaries
        final_dict = {**alphabet_dict, **numeric_dict}
        final_lookup = {**alphabet_lookup, **numeric_lookup}

        # Add in shift and return keys
        for i in [160, 161, 162, 13, 164, 9]:
            final_dict[i] = len(final_dict)

        final_lookup['LShift'] = 36
        final_lookup['RShift'] = 37
        final_lookup['Ctrl'] = 38
        final_lookup['Return'] = 39
        final_lookup['Enter'] = 39
        final_lookup['Alt'] = 40
        final_lookup['Tab'] = 41

        self.dict = final_dict
        self.lookup = final_lookup

    def convert(self, qt_kc):
        if qt_kc in self.dict:
            return self.dict[qt_kc]
        else:
            return None

    def get_code(self, key):
        if key.upper() in self.lookup.keys():
            return self.lookup[key.upper()]
        else:
            return None

    def get_key(self, code):
        return next(key for key, value in self.lookup.items() if value == code)

    def get_n_keys(self):
        return len(self.dict.keys())


vkconvert = VKKeyCode2KeyStoreKeyCode()


class GroupingBuffer(object):
    def __init__(self, holdkey_matrix):
        self.events = []
        # This is a failsafe variable designed to prevent the system
        # from hanging in the event that there is a stuck key in the buffer
        self.count_returns = 0
        self.num_downs = 0
        self.num_ups = 0
        self.holdkey_matrix = holdkey_matrix

    def get_event_offset(self, action, pos):
        """
        Args:
            action: 'D' or 'U'
            pos: offset from the start of the queue
        """
        act_c = 0
        for i in range(len(self.events)):
            if self.events[i].action == action:
                act_c += 1
                if act_c == pos:
                    return self.events[i]
        return None

    def get_event_key(self, action, key, start_time=None):
        """
        Args:
            action: 'D' or 'U'
            key: the key for which the action is desired
        """
        for i in range(len(self.events)):
            if (self.events[i].key == key) & (self.events[i].action == action):
                if start_time is not None:
                    if self.events[i].time > start_time:
                        return self.events[i]
                else:
                    return self.events[i]
        return None

    def add_event(self, buffer_event):
        # if len(self.events) > 0:
        if self.events:  # Check if the list is empty or not
            # pop all the deleted or Up actions from the start of the list
            while (self.events[0].delete) or (self.events[0].action == 'U'):
                if self.events[0].action == 'D':
                    self.num_downs -= 1
                else:
                    self.num_ups -= 1

                self.events.pop(0)

        # Add the new event to the end of the buffer
        self.events.append(buffer_event)
        if buffer_event.action == 'D':
            self.num_downs += 1
        else:
            self.num_ups += 1

        # Check if there are 4 Down events in the buffer
        if self.num_downs >= 4:
            # Check if the second down event has a corresponding up event
            s_down = self.get_event_offset('D', 2)
            s_up = self.get_event_key('U', s_down.key)

            if (s_up is not None):
                if (s_up.time < s_down.time):
                    # This likely means that we are looking at a double letter press
                    s_up = self.get_event_key('U', s_down.key, s_down.time)

            if (s_down is not None) & (s_up is not None):
                f_down = self.get_event_offset('D', 1)
                a_down = self.get_event_offset('D', 3)

                if a_down is None:
                    for e in self.events:
                        print("{}:{}", e.key, e.action)
                f_down.delete = True
                # print("{}F {}D {}U".format(f_down.time,s_down.time,s_up.time))
                # Exctract the 1,2,3 hold time.
                # print("{} has a hold time of {}ms when preceeded by {} and followed by {}".format(s_down.key,1000*(s_up.time-s_down.time),f_down.key,a_down.key))
                prior = vkconvert.convert(f_down.key)
                key = vkconvert.convert(s_down.key)
                post = vkconvert.convert(a_down.key)
                if (prior is not None) & (key is not None) & (post is not None):
                    # Add this to the holdkey matrix
                    # print("Adding key data {} {} {}".format(prior,key,post))
                    self.holdkey_matrix.get_key_distribution(prior, key, post).add_timing(
                        1000 * (s_up.time - s_down.time))
            else:
                # It is likely the case that we have a stuck key, so allow this to go on
                # until we have 10 down events queued, then pop the top down event and set the second down event to delete to un stick it
                if self.num_downs >= 6:
                    print("Popping the top event and setting the delete flag on {} since it seems to be stuck".format(
                        s_down.key))
                    self.events[0].delete = True
                    s_down.delete = True


class TriGraphDataCollector(object):
    def __init__(self):
        self.holdkey_matrix = HoldKeyMatrix(vkconvert.get_n_keys())
        self.grp_buffer = GroupingBuffer(self.holdkey_matrix)
        self.num_keys_collected = 0

    def add_event(self, scan_code, action, time):
        # self.grp_buffer.AddEvent(BufferEventElement(_os_keyboard.scan_code_to_vk[e.scan_code],e.event_type,e.time))
        self.grp_buffer.add_event(BufferEventElement(scan_code, action, time))
        self.num_keys_collected += 1

    def save_state(self, file_path, clear_state=False):
        # We want to save the current state of the hold key matrix
        self.holdkey_matrix.save_state(file_path)
        # if clear_state:
        # Remove the current reference
        #  del self.holdkey_matrix
        # Recreate the holdkey matrix
        # self.holdkey_matrix = np.array([[[KeyHoldDistribution(b,c,a) for a in range(38)] for b in range(38)] for c in range(38)])

    def load_state(self, file_path):
        self.holdkey_matrix.load_state(file_path)
        print("Loaded {} holdkey matrix".format(file_path))

    def print_stats(self):
        print("Collected {} keys so far\n Holdkey contains {} Events".format(self.num_keys_collected,
                                                                             self.holdkey_matrix.number_of_total_events()))


class HoldKeyMatrix(object):
    def __init__(self, n_keys):
        self.holdkey_matrix = nparray(
            [[[KeyHoldDistribution(b, c, a) for a in range(n_keys)] for b in range(n_keys)] for c in range(n_keys)])
        self.n_keys = n_keys

    def save_state(self, file_path):
        npsave(file_path, self.holdkey_matrix)

    def load_state(self, file_path):
        self.holdkey_matrix = npload(file_path, allow_pickle=True).copy()

    def get_key_distribution(self, prior, key, post):
        if (prior <= self.n_keys) & (key <= self.n_keys) & (post <= self.n_keys):
            return self.holdkey_matrix[prior, key, post]

    def number_of_total_events(self):
        n_timing = 0
        for i in range(self.n_keys):
            for j in range(self.n_keys):
                for k in range(self.n_keys):
                    n_timing += len(self.holdkey_matrix[i, j, k].timings)
        return n_timing

    def __add__(self, other):
        assert (
                self.holdkey_matrix.shape == other.holdkey_matrix.shape), "Holdkey matricies must be the same shape to combine!"
        assert (self.n_keys == other.n_keys), "Holdkey matrices must support the same number of keys to combine!"
        hkm_new = HoldKeyMatrix(self.n_keys)
        hkm_new.holdkey_matrix = (self.holdkey_matrix + other.holdkey_matrix)
        return hkm_new
