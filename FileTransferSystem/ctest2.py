import sys
from thespian.actors import ActorSystem, Actor, ActorTypeDispatcher, ActorExitRequest
import logging
import select
import socket
import errno
from datetime import timedelta
from functools import partial
from common import *
import Actors
import time
import signal
import uuid

#capabilities = {'Convention Address.IPv4': ('10.128.108.62', 2212), 'Admin Port': 2213, 'uuid': None}
capabilities = {'Admin Port': 2213, 'uuid': None}
if __name__ == "__main__":
    capabilities['uuid'] = uuid.uuid4().hex
    asys = ActorSystem('multiprocTCPBase', capabilities)
    print("Joining Convention")
    asys.updateCapability('Convention Address.IPv4',('10.128.108.62', 2212))
    time.sleep(2)
    rn = asys.createActor('Actors.RegistrarActor', {'uuid': capabilities['uuid']}, globalName='rnode')
    asys.tell(rn, 'Hello String')
    time.sleep(1)
    # la = asys.createActor(Actors.LogActor)
    # asys.tell(la,"init")
    # time.sleep(2)
    print("Shutting Down")
    asys.tell(rn, ActorExitRequest())
    time.sleep(3)
    asys.shutdown()
