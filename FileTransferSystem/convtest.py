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
import messages

capabilities = {'Convention Address.IPv4': ('10.128.108.62', 2212), 'Admin Port': 2212}


def signal_handler(sig, frame):
    print('Shutting Down')
    asys = ActorSystem('multiprocTCPBase', capabilities)
    asys.tell(la, ActorExitRequest)
    asys.shutdown()
    exit(0)


def startup():
    signal.signal(signal.SIGINT, signal_handler)


if __name__ == "__main__":
    print(capabilities)
    asys = ActorSystem('multiprocTCPBase', capabilities)
    la = asys.createActor('ConventionLead.Registrar')
    asys.tell(la, messages.InitPacket())
    time.sleep(15)
    print("Shutting Down")
    asys.tell(la, ActorExitRequest)
    time.sleep(3)
    asys.shutdown()
