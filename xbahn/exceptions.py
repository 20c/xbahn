# CONNECTION

class SchemeNotFound(KeyError):
    def __init__(self, scheme):
        super(KeyError, self).__init__("'%s' is not a known scheme" % scheme)

class TimeoutError(IOError):
    def __init__(self, action, timeout):
        super(IOError, self).__init__("timeout of %.2f seconds exceeded for '%s'" % (timeout, action))

# API

class APIError(IOError):
    pass
