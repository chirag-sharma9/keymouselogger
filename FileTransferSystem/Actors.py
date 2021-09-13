from thespian.actors import ActorSystem, Actor, ActorTypeDispatcher


class LogActor(ActorTypeDispatcher):
    def __init__(self):
        super().__init__()
        print("Log Actor Started")

    @staticmethod
    def actorSystemCapabilityCheck(capabilities, requirements):
        return capabilities.get('Blarg', None) == requirements['Blarg']

    def receiveMsg_str(self, msg, sender):
        if msg == 'init':
            self.notifyOnSystemRegistrationChanges(True)
            print("Registered for System updates")
        else:
            print("Str Msg: {}".format(msg))

    def receiveMsg_ActorExitRequest(self, msg, sender):
        print("Recv Shutdown Request")

    def receiveMsg_ActorSystemConventionUpdate(self, msg, sender):
        print("New ActorSystem Added to Convention")
        print(msg.remoteAdminAddress)
        print(msg.remoteCapabilities)
        print(msg.remoteAdded)


class RegistrarActor(ActorTypeDispatcher):
    def __init__(self):
        print("Rnode actor started")

    @staticmethod
    def actorSystemCapabilityCheck(capabilities, requirements):
        return capabilities.get('uuid', None) == requirements['uuid']

    def receiveMsg_str(self, msg, sender):
        print(msg)
