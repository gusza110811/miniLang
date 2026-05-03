import type
import typing

class Context:
    def __init__(self,parent:"Context"=None):
        self.parent = parent
        self.root = parent is None
        self.next = 0
        self.next_param = 0
        self.data:dict[type.T] = {}
    
    def __repr__(self):
        return "root" if self.root else repr(self.parent) + f">Context()"

    def get(self, key:str) -> type.T:
        val = self.data.get(key)
        if (val is None) and not self.root:
            val = self.parent.get(key)
        return val
    
    def get_all(self):
        return self.data

    def check(self,key:str):
        return False if self.data.get(key) is None else True

    def add(self, key:str, t:typing.Literal["char","int","ptr"]):
        val = type.get(t)
        if not val:return

        self.next += val.size
        val.pos = -self.next

        self.data[key] = val
        return val

    def add_param(self, key:str, t:typing.Literal["char","int","ptr"]):
        val = type.get(t)
        if not val:return

        self.next_param += val.size
        val.pos = self.next_param

        self.data[key] = val
        return val
