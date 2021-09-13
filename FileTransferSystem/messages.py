class InitPacket(object):
    def __init__(self):
        self.init_settings = {}


class RequestRegistration(object):
    def __init__(self, name, address):
        self.name = name
        self.address = address


class RegistrationAck(object):
    def __init__(self, accepted, reason=None):
        self.accepted = accepted
        self.reason = reason


class AddressRequest(object):
    def __init__(self, name):
        self.name = name


class RegistrarAddress(object):
    def __init__(self, reg_address):
        self.red_address = reg_address


class AddressResponse(object):
    def __init__(self, found, address):
        self.found = found
        self.address = address
