from __future__ import annotations
from typing import TYPE_CHECKING
from lark import Lark, Transformer as t
import lark
import os, sys
import typing
from context import Context
from dataclasses import dataclass

@dataclass
class ParseErr(Exception):
    msg:str
    line:int
    col:int
    colend:int
    hint:str=""

__dir__ = os.path.dirname(__file__)

class Transformer(t):
    class Node:
        def __init__(self, value):pass
        
        def eval(self, context:Context=None):pass

        def __repr__(self):
            return f"<Invalid Node>"
        
        def get_first_token(self) -> lark.Token:
            return
        
        def get_last_token(self) -> lark.Token:
            return

    class Branch(Node):
        def __init__(self, value:list[Transformer.Node]):
            self.children = value
        
        def eval(self, context:Context):
            pass

        def get_first_token(self):
            tokens = [child.get_first_token() for child in self.children if child]
            tokens = list(filter(lambda c: isinstance(c,lark.Token), tokens))
            return tokens[0]
        
        def get_last_token(self):
            tokens = [child.get_last_token() for child in self.children if child]
            tokens = list(filter(lambda c: isinstance(c,lark.Token), tokens))
            return tokens[-1]
        
        def __repr__(self):
            return f"{self.__class__.__name__}({self.children})"
    
    class Leaf(Node):
        def __init__(self, token):
            self.value = token.value
            self.token:lark.Token = token
        
        def eval(self):
            return self.value
        
        def get_first_token(self):
            return self.token
        
        def get_last_token(self):
            return self.token
        
        def __repr__(self):
            return f"{self.__class__.__name__}({self.value})"

    class Codegen(Branch):
        def collect(self, context:Context):
            return [""]
        def emit(self) -> list[str]:
            return [""]

    class start(Codegen):
        children:list[Transformer.Codegen]
        def __repr__(self):
            return "\n".join([repr(child) for child in self.children])
        
        def eval(self, context):
            for child in self.children:
                child.eval(context)
        
        def collect(self, context):
            for child in self.children:
                child.collect(context)
        
        def emit(self):
            out = []
            for child in self.children:
                out.extend(child.emit())
            
            return out
    
    class scope(Branch):
        def __repr__(self):
            return "{\n" + "\n".join(["  " + repr(child) for child in self.children]) + "\n}"

    class func_def(Branch):
        def __init__(self, value):
            super().__init__(value)
            self.type = self.children[0]
            self.name = self.children[1]
            self.parameters = self.children[2:-1]
            self.statement = self.children[-1]

        def __repr__(self):
            return (repr(self.name) + "(" + ",".join([repr(param) for param in self.parameters]) + ")" + " -> " + repr(self.type) + repr(self.statement))
    
    class declaration(Codegen):
        def __init__(self, value):
            super().__init__(value)
            self.type:Transformer.IDENTIFIER = self.children[0]
            self.name:Transformer.IDENTIFIER = self.children[1]
            self.value:Transformer.expr = self.children[2]
        
        def eval(self, context):
            self.type = self.type.eval()
            self.name = self.name.eval()
            result = context.add(self.name,self.type)
            if not result:
                raise ParseErr("asdasd",1,1,1)
            self.size = result.size

        def collect(self, context):
            self.out = []
            self.out.extend(self.value.eval(context))
            self.out.extend([
                "pop ax",
                f"mov " + "[" + ("b" if self.size == 1 else "w") + f" bp-{context.get(self.name).pos}]" + ", ax"
            ])
        
        def emit(self):
            return self.out
        
        def __repr__(self):
            return repr(self.type) + " " + repr(self.name) + " = " + repr(self.value)
    class assignment(Codegen):
        def __init__(self, value):
            super().__init__(value)
            self.name = self.children[0]
            self.value = self.children[1]

        def eval(self, context):
            self.name = self.name.eval()
            if not context.check(self.name):
                raise ParseErr("undefined!!",1,1,1)

        def collect(self, context):
            self.out = []
            self.out.extend(self.value.eval(context))
            self.out.extend([
                "pop ax",
                f"mov " + "[" + ("b" if self.size == 1 else "w") + f" bp-{context.get(self.name).pos}]" + ", ax"
            ])
        
        def emit(self):
            return self.out
        
        def __repr__(self):
            return repr(self.name) + " = " + repr(self.value)

    class expr(Branch):
        def __init__(self, value):
            super().__init__(value)
            self.lhs = self.children[0]
            self.rhs = self.children[1]

    class add(expr):
        def eval(self, context):
            out = []

            out.extend(self.lhs.eval(context))
            out.extend(self.rhs.eval(context))
            
            out.extend([
                "pop dx",
                "pop ax",
                "add ax, dx",
                "push ax"
            ])

            return out

    class literal(Branch):
        def __init__(self, value):
            super().__init__(value)
            self.value = self.children[0]
        
        def eval(self, context):
            return [
                f"mov ax, {self.value.eval()}",
                "push ax"
            ]

        def __repr__(self):
            return "literal " + repr(self.value)
    
    class symbol(Branch):
        def __init__(self, value):
            super().__init__(value)
            self.value = self.children[0]
        
        def eval(self, context):
            name = self.value.eval()
            result = context.get(name)
            if not result:
                raise ParseErr("undefined!!!!",1,1,1)
            size = result.size
            index = result.pos

            return [
                f"mov ax, " + "[" + ("b" if size == 1 else "w") + f" bp-{index}]"
            ]

    class DECIMAL(Leaf):
        def __repr__(self):
            return self.value

    class IDENTIFIER(Leaf):
        def __repr__(self):
            return "identifier " + self.value

class Parser:
    def __init__(self):
        self.grammar = open(os.path.join(__dir__,"grammar.lark")).read()
        self.parser = Lark(
            self.grammar,
            parser="lalr",
        )
        self.transformer = Transformer()
    def parse(self, code:str, filename="<main>"):
        transformer = self.transformer
        parser = self.parser

        parsedTree = parser.parse(code)

        tree = transformer.transform(parsedTree)

        return tree
