mapping = {}

class T:
    size:int = None
    pos:int = None

def register(name,type):
    mapping[name] = type

def get(name) -> T:
    return mapping.get(name)()

class Void(T):
    size = 0
register("void",Void)

class Char(T):
    size = 1
register("char",Char)

class Int(T):
    size = 2
register("int",Int)

class Ptr(T):
    size = 2
    targetsize = 0
register("ptr",Int)
