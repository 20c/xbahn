def append(*args):
    return ".".join([a.strip(".") for a in args if a != ""])

def split(path):
    return path.split(".")

def walk(path):
    r = ""
    for p in split(path):
        r = append(r, p)
        yield r

def match(a, b):
    a = split(a)
    b = split(b)

    if len(a) > len(b):
        return False
    n = 0
    for x in a:
        if b[n] != x:
            return False
        n+=1
    return True

def tail(prefix, path):
    a = split(path)
    b = split(prefix)
    r = []
    for x in a:
        if b:
            if b.pop(0) == x:
                continue
            else:
                return []
        r.append(x)
    return r

