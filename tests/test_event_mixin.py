from xbahn.mixins import EventMixin

def test_callback():

    """
    Test adding a callback for an event
    """

    obj = EventMixin()

    data = { "a" : 1 }
    expected = { "a" : 2, "b": 3 }

    # the callback will increase the value
    # of data.a everytime it is triggered
    def callback(val, event_origin=None):
        data["a"] += val

    # attach callback to event
    obj.on("increase", callback)

    # trigger event (val=1)
    obj.trigger("increase", 1)

    assert data["a"] == expected["a"]

    # trigger event (val=1)
    obj.trigger("increase", 1)

    assert data["a"] == expected["b"]


def test_event_origin():

    """
    Test that event_origin references is passed
    correctly to callbacks
    """

    obj = EventMixin()

    def callback(event_origin=None):
        assert event_origin == obj

    obj.on("test", callback)
    obj.trigger("test")


def test_callback_once():

    """
    Test that callbacks attached with the once flag
    will only be triggered once and removed afterwards
    """

    obj = EventMixin()

    data = { "a" : 1 }
    expected = { "a" : 2 }

    def callback(val, event_origin=None):
        data["a"] += val

    obj.on("increase", callback, once=True)
    obj.trigger("increase", 1)

    assert data["a"] == expected["a"]

    # at the second time the event triggers, the callback
    # is no longer attached, so the value in data.a should
    # remain the same
    obj.trigger("increase", 1)

    assert data["a"] == expected["a"]

def test_callback_remove():

    """
    Test removing of callbacks via the "off" method
    """

    obj = EventMixin()

    def callback(event_origin=None):
        return

    obj.on("test", callback)

    assert (callback, False) in obj.event_listeners["test"]

    obj.off("test", callback)

    assert (callback, False) not in obj.event_listeners["test"]

    obj.on("test", callback, once=True)

    assert (callback, True) in obj.event_listeners["test"]
    assert (callback, False) not in obj.event_listeners["test"]

    obj.off("test", callback, once=True)

    assert (callback, True) not in obj.event_listeners["test"]
