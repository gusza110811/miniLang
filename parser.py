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
                if not isinstance(child,Transformer.func_def):
                    raise ParseErr("non func in global")
                child.eval(context)
        
        def collect(self, context):
            for child in self.children:
                child.collect(context)
        
        def emit(self):
            out = []
            for child in self.children:
                out.append(child.emit())
            
            return out
    
    class scope(Codegen):
        context:Context

        def __repr__(self):
            return "{\n" + "\n".join(["  " + repr(child) for child in self.children]) + "\n}"
        
        def eval(self, context):
            self.context = Context(context)
            for child in self.children:
                child.eval(self.context)
        
        def collect(self, context):
            for child in self.children:
                child.collect(self.context)
        
        def emit(self):
            out = [(self.context,)]
            for child in self.children:
                out.extend(child.emit())
            
            return out
    class func_def(Branch):
        def __init__(self, value):
            super().__init__(value)
            self.type = self.children[0]
            self.name = self.children[1]
            self.parameters = self.children[2:-1]
            self.statement:Transformer.scope = self.children[-1]
        
        def eval(self, context):
            self.type = self.type.eval()
            self.name = self.name.eval()

            for child in self.parameters:
                child.eval(context)
            
            self.statement.eval(context)

        def collect(self, context):
            self.statement.collect(context)

        def emit(self):
            out = [("label",self.name)]
            out.extend(self.statement.emit())
            out.append(("ret"))
            return out

        def __repr__(self):
            return (repr(self.name) + "(" + ",".join([repr(param) for param in self.parameters]) + ")" + " -> " + repr(self.type) + repr(self.statement))
    
    class asm(Codegen):
        def collect(self, context):
            self.out = self.children[0].eval(context)
        def emit(self):
            return [("asm",self.out)]
    class strings(Branch):
        def eval(self, context):
            values = []
            for child in self.children:
                values.append(child.eval())
            return "\n".join(values)

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
            self.pos = result.pos

        def collect(self, context):
            self.out = []
            if self.value:
                self.out.extend(self.value.eval(context))
            if self.value:
                self.out.append(("set",self.name))
        
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
            result = context.get(self.name)
            self.size = result.size
            self.pos = result.pos

        def collect(self, context):
            self.out = []
            self.out.extend(self.value.eval(context))
            self.out.extend([
                ("set",self.name)
            ])
        
        def emit(self):
            return self.out
        
        def __repr__(self):
            return repr(self.name) + " = " + repr(self.value)

    class binary_op(Branch):
        name = ""
        commutative = False

        def __init__(self, value):
            super().__init__(value)
            self.lhs = self.children[0]
            self.rhs = self.children[1]
        
        def eval(self, context):
            out = []

            lhs = self.lhs.eval(context)
            rhs = self.rhs.eval(context)

            if lhs[-1][0] == "lit" and self.commutative:
                lhs, rhs = rhs, lhs

            out.extend(lhs)
            out.extend(rhs)
            out.append((self.name,))

            return out

    class add(binary_op):
        name = "add"
        commutative = True

    class literal(Branch):
        def __init__(self, value):
            super().__init__(value)
            self.value = self.children[0]
        
        def eval(self, context):
            return [
                ("lit",self.value.eval())
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
            tok = self.value.get_first_token()
            if not result:
                raise ParseErr("undefined!!!!",tok.line-1,tok.column-1,tok.end_column-1)

            return [
                ("get",name)
            ]

    class DECIMAL(Leaf):
        def eval(self):
            return int(self.value)

        def __repr__(self):
            return self.value
    
    class HEX(Leaf):
        def eval(self):
            return int(self.value[2:],base=16)
        def __repr__(self):
            return self.value
    class BINARY(Leaf):
        def eval(self):
            return int(self.value[2:],base=2)
        def __repr__(self):
            return self.value
    class OCTAL(Leaf):
        def eval(self):
            return int(self.value[2:],base=8)
        def __repr__(self):
            return self.value

    class IDENTIFIER(Leaf):
        def __repr__(self):
            return "identifier " + self.value
    
    class STRING(Leaf):
        def __repr__(self):
            return "string " + self.value
        
        def eval(self):
            return self.value[1:-1]

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
