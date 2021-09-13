
# BEE Structure stores data about the keystroke
class BufferEventElement(object):
    def __init__(self, key, action, time):
        self.key = key
        self.action = action
        self.time = time
        self.delete = False


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
            while self.events[0].delete or (self.events[0].action == 'U'):
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