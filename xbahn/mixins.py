from builtins import str
from builtins import object
import logging

class LogMixin(object):
    @property
    def log(self):
        return logging.getLogger("xbahn")

    @property
    def log_component_name(self):
        return "[%s]" % str(self)

    def log_message(self, msg, level="debug"):
        fn = getattr(self.log, level)
        fn("%s%s" % (self.log_component_name, msg))

    def log_debug(self, msg):
        self.log_message(msg)

    def log_error(self, msg):
        self.log_message(msg, level="error")



class EventMixin(object):

    """
    Adds event triggering / listening functionality
    """

    def __init__(self):
        self.event_listeners = {}

    def has_callbacks(self, name):
        """
        Returns True if there are callbacks attached to the specified
        event name.

        Returns False if not
        """
        r = self.event_listeners.get(name)
        if not r:
            return False
        return len(r) > 0

    def on(self, name, callback, once=False):
        """
        Adds a callback to the event specified by name

        once <bool> if True the callback will be removed once it's been
        triggered
        """
        if name not in self.event_listeners:
            self.event_listeners[name] = []

        self.event_listeners[name].append((callback, once))

    def off(self, name, callback, once=False):
        """
        Removes callback to the event specified by name
        """

        if name not in self.event_listeners:
            return

        self.event_listeners[name].remove((callback, once))

    def trigger(self, name, *args, **kwargs):
        """
        Triggers the event specified by name and passes
        self in keyword argument "event_origin"

        All additional arguments and keyword arguments are passed
        through as well
        """

        mark_remove = []
        for callback, once in self.event_listeners.get(name, []):
            callback(event_origin=self, *args, **kwargs)
            if once:
                mark_remove.append( (callback, once) )

        for callback, once in mark_remove:
            self.off(name, callback, once=once)
