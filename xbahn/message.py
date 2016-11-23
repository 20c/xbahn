"""
Message objects
"""
from builtins import str

import uuid

from xbahn.mixins import EventMixin

import munge
import munge.codec.all

class Message(EventMixin, object):

    """
    Base Message class

    data <mixed> - the main content of the message

    Any additional argument or keyword argument will also stored in
    the args and kwargs properties.
    """

    def __init__(self, data, *args, **kwargs):
        EventMixin.__init__(self)
        self.meta = {}
        self.data = data
        self.args = args
        self.kwargs = kwargs
        self.meta.update(id=str(uuid.uuid4()))
        self.responder = None
        self.response_received = False
        self.response_message = None
        self.responded = False

    def __repr__(self):
        return "MSG %s: %s (-> %s)" % (self.id, self.path, self.response_id)

    def __dict__(self):
        return {
            "meta" : self.meta,
            "data" : self.data,
            "args" : self.args,
            "kwargs" : self.kwargs
        }

    @property
    def path(self):
        """
        Return the xbahn path of this message
        """
        return self.meta.get("path", "")

    @property
    def id(self):
        """
        Return the id of this message, automatically assigned on
        creation
        """
        return self.meta.get("id")

    @property
    def response_id(self):
        """
        Return the response id of this message, this is only set
        when the message is intended to be a response to an earlier
        message
        """
        return self.meta.get("response_id")

    def export(self, contentType):
        """
        Export message to specified contentType via munge

        contentType <str> - eg. "json", "yaml"
        """
        cls = munge.get_codec(contentType)
        codec = cls()
        return codec.dumps(self.__dict__())

    def response(self, message=None, event_origin=None):
        self.trigger("response", message, source=event_origin)

    def attach_response(self, message=None, event_origin=None):
        self.response_received = True
        self.response_message = message


class ErrorMessage(Message):
    def __init__(self, errmsg):
        Message.__init__(self, None)
        self.meta.update(error=errmsg)
