import unittest
from thespian.actors import ActorSystem, Actor, ActorTypeDispatcher, ActorExitRequest
from thespian.system import multiprocTCPBase
import uuid
import time
import messages


class ConventionTests(unittest.TestCase):

    def setUp(self):
        self.sys1 = None
        self.sys2 = None
        self.sys2_capabilities = None
        self.sys1_capabilities = None

        print("Starting Main System")
        self.sys1_capabilities = {'Convention Address.IPv4': ('10.128.108.62', 2219), 'Admin Port': 2211}
        self.sys1 = ActorSystem('multiprocTCPBase', capabilities=self.sys1_capabilities)

        # Create the registrar on System 1 and send an Init Packet
        self.registrar = self.sys1.createActor('ConventionLead.Registrar')
        self.sys1.tell(self.registrar, messages.InitPacket())

    def test_simple_message(self):
        # Create System 2 and have it join the convention, this will force the registrar to create an actor on system2
        self.sys2_capabilities = {'Convention Address.IPv4': ('10.128.108.62', 2219), 'Admin Port': 2215,
                                  'uuid': uuid.uuid4().hex}
        # the uuid is included here to uniquely identify system2 from other actor systems so the registrar can create
        # an actor on this system
        self.sys2 = ActorSystem(capabilities=self.sys2_capabilities)

        print(self.sys2_capabilities)

        try:
            rn = self.sys2.createActor('Actors.RegistrarActor', {'uuid': self.sys2_capabilities['uuid']},
                                       globalName='rnode')
            self.assertEqual(rn, self.registrar.rnodes[self.sys2_capabilities['uuid']])
            self.sys2.tell(rn, 'Hello String Me')

            self.sys2.tell(rn, ActorExitRequest(True))
        finally:
            print("Shutting Down System 2")
            self.sys2.shutdown()

    def tearDown(self):
        self.sys1.tell(self.registrar, ActorExitRequest())
        self.sys1.shutdown()


if __name__ == "__main__":
    unittest.main()
