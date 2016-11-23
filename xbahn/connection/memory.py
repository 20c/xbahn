from xbahn.connection import (
    register,
    Poller as BasePoller,
    Receiver as BaseReceiver,
    Sender as BaseSender
)

receivers = {}
senders = {}

class Poller(BasePoller):
    def __init__(self, name):
        super(Poller, self).__init__()
        self.name = name

class Receiver(BaseReceiver):
    can_send = True

    def __init__(self, name):
        super(Receiver, self).__init__()
        receivers[name] = self
        self.name = name

    def send(self, data):
        for sender in senders.get(self.name, []):
            sender.receive(data, eventOrigin=self)

    def close(self):
        try:
            del senders[self.name]
            del receivers[self.name]
        except KeyError:
            pass

class Sender(BaseSender):
    can_receive = True
    responder = True

    def __init__(self, name):
        super(Sender, self).__init__()
        if name not in senders:
            senders[name] = []
        senders[name].append(self)
        self.name = name

    @property
    def receiver(self):
        return receivers.get(self.name)

    def send(self, data):
        self.receiver.receive(data, eventOrigin=self)

    def respond(self, data):
        self.receive(data, eventOrigin=self)

    def close(self):
        senders[self.name].remove(self)

@register('memory')
def sender(u):
    return Sender(u.hostname)

@register('memory')
def receiver(u):
    return Receiver(u.hostname)

@register('memory')
def poller(u):
    return Poller(u.hostname)
