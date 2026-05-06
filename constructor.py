from __future__ import annotations
from typing import TYPE_CHECKING, Literal
from context import Context
from parser import Transformer
from dataclasses import dataclass

@dataclass
class action:
    pushed_ax:bool
    popped_ax:bool
    pushed_dx:bool
    popped_dx:bool

class Constructor:
    def __init__(self):
        self.globals = Context()
        self.ir:list[list[tuple]]
        self.out = ""

    def main(self,ast:Transformer.start,filename="<main>") -> str:
        "produce IR"
        contexts = ast.eval(self.globals)

        ast.collect(self.globals)
        #print([context.data for context in contexts])
        #print(self.globals.data)

        self.ir = ast.emit()
        print(self.ir)
        
        print("\n---\n")

        dirty = True
        while dirty:
            self.ir, dirty = self.optimize(self.ir)
        print(self.ir)

        self.out = self.lower(self.ir)
        print(self.out)

        return "\n".join(self.out)

    def optimize(self,scope,context:Context=None):
        if not context:
            context = self.globals
        idx = 0
        def next():
            nonlocal idx
            if idx < len(scope):
                val = scope[idx]
            else:
                val = ("")
            idx += 1
            return val
        
        def end():
            if idx >= len(scope):
                return True
            else:
                return False

        dirty = False

        out = []

        prev = ("",)
        while 1:
            #print(out)
            if end():break
            current = next()

            command = current[0]
            prev_command = prev[0]

            matched=True
            match command:
                case "scope":
                    result, checkdirty = self.optimize(current[2],current[1])
                    dirty |= checkdirty
                    out.append(("scope",current[1],result))

                case _:
                    matched = False
            if matched:continue

            match (command,prev_command):
                case "add","lit":
                    dirty = True
                    out.pop()
                    if prev[1] != 0:
                        out.append(("addi",prev[1]))
                case "addi","lit":
                    dirty = True
                    out.pop()
                    if prev[1] != 0:
                        out.append(("lit",prev[1]+current[1]))
                case _:
                    out.append(current)

            prev = current

        return out, dirty

    def lower(self,scope:list[tuple],context:Context=None):
        if not context: context = self.globals
        idx = 0
        def next():
            nonlocal idx
            if idx < len(scope):
                val = scope[idx]
            else:
                val = ("")
            idx += 1
            return val
        
        def end(offset=0):
            if (idx+offset) >= len(scope):
                return True
            else:
                return False
        
        out = []

        for var in context.get_all().values():
            if var.size == 1:
                out.append("pushb ax")
            else:
                out.append("push ax")

        prev = ("")
        current = ("")
        after = next()
        prev_action = action(False,False,False,False)
        current_action = action(False,False,False,False)
        active_register:Literal["ax","dx"] = "ax" # ax or dx

        def swap():
            nonlocal active_register
            if active_register == "ax":
                active_register = "dx"
            else:
                active_register = "ax"
        def reset():
            nonlocal active_register
            active_register = "ax"
        while 1:
            if end(-1):break
            prev, current, after = current, after, next()
            prev_action = current_action

            prevcommand = current[0]
            command = current[0]
            aftercommand = current[0]

            match command:
                # push
                case "get"|"lit":
                    if active_register == "ax":
                        current_action = action(False,False,True,False)
                    else:
                        current_action = action(True,False,False,False)
                # pop
                case "set":
                    if active_register == "ax":
                        current_action = action(False,True,False,False)
                    else:
                        current_action = action(False,False,False,True)
                # push and pop
                case "add"|"addi":
                    if active_register == "ax":
                        current_action = action(True,True,False,True)
                    else:
                        current_action = action(False,True,True,True)
                
                case _:
                    current_action = action(False,False,False,False)
            
            #print(context,current_action)

            if prev_action.pushed_ax:
                if not current_action.popped_ax:
                    out.append("push ax")
            if prev_action.pushed_dx:
                if not current_action.popped_dx:
                    out.append("push dx")

            if current_action.popped_ax:
                if not prev_action.pushed_ax:
                    out.append("pop ax")
            if current_action.popped_dx:
                if not prev_action.pushed_dx:
                    out.append("pop dx")

            #print(current_action)
            match command:
                # neither
                case "asm":
                    reset()
                    out.append(current[1])
                
                case "scope":
                    out.append("{")
                    out.extend(self.lower(current[2],current[1]))
                    out.append("}")
                
                case "label":
                    out.append(current[1] + ":")
                
                case "declare":
                    key = current[1]
                    rep = context.get(key)
                    pos = str(rep.pos)
                    size = "w" if rep.size == 2 else "b"

                    out.append(key + " = " + pos)

                # pop
                case "set":
                    key = current[1]
                    rep = context.get(key)
                    size = "w" if rep.size == 2 else "b"

                    out.append("mov [" + size + " bp + " + key + "], " + active_register)

                case "ret":
                    out.append("ret") # temporary

                # pop and push
                case "add":
                    swap()
                    line = "add " + active_register + ", "
                    swap()
                    line += active_register
                    swap()
                    out.append(line)
                case "addi":
                    line = "add " + active_register + ", "
                    line += str(current[1])
                    out.append(line)

                # push
                case "lit":
                    swap()
                    out.append("mov " + active_register + ", " + str(current[1]))
                case "get":
                    key = current[1]
                    rep = context.get(key)
                    pos = str(rep.pos)
                    size = "w" if rep.size == 2 else "b"
                    positive = "+" if rep.pos >= 0 else ""

                    swap()
                    out.append("mov " + active_register +", [" + size + " bp " + positive + pos + "]")
        
        return out

