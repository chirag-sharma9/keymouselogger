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

    def getActiveApp(self):
        return self.active_app


    def receiveMessage(self, message, sender):

        kibanaActorMouse = self.createActor(UploadMousetoKibana, globalName="UploadMousetoKibana")

        if isinstance(message, dict):
            print('mouse event check!!!')
            if "mbe" in message:
                print('mbe check!!!!!!')
                if message['app'] is not None:
                    if message['app'] in self.filter_apps:
                        print(f"Filtered App [{message['app']}]")
                        return
                e = message['mbe']

                self.cur_time = (e.elapsed_time*pow(10,9))+self.boot_time

                print(f'current time:{self.cur_time}')
                if len(self.mouse_data) == 0:
                    self.first_mouse_time = self.cur_time
                    self.prev_mouse_time = self.cur_time
                else:
                    prev_time_elapsed = float(self.mouse_data[-1][1])
                    self.prev_mouse_time = (prev_time_elapsed*pow(10,9))+self.boot_time

                self.mouse_data.append((e.app, str(e.elapsed_time), e.button, e.action, str(e.x), str(e.y)))

                if checkUploadTime(self.cur_time, self.first_mouse_time, self.prev_mouse_time):
                    mouse_buffer = self.mouse_data.copy()
                    self.send(kibanaActorMouse, mouse_buffer)
                    self.mouse_data.clear()
                    self.first_mouse_time = 0
                    self.prev_mouse_time = 0


class UploadMousetoKibana(Actor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # replace with kibana consumer stuff
        self.file_path = 'mouse_data.csv'

    def receiveMessage(self, message, sender):
        if not isinstance(message, list):
            print('not a list')
            return

        if not self.file_path.endswith('.csv'):
            file_path += '.csv'

        #Open the output file
        print('Writing to file now...')
        print(message)
        with open(self.file_path,'a') as f:
            for i in range(len(message)):
                kd = message[i]
                if kd is None:
                    print("Skipping mouse due to none type...")
                    continue
                f.writelines([",".join(kd) + "\n"])
