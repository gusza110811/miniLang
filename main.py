#!/usr/bin/python3
import parser, constructor, color
import os, sys
import argparse
import lark.exceptions

__dir__ = os.path.dirname(__file__)

class Assembler:
    def __init__(self):
        self.parser = parser.Parser()
        self.constructor = constructor.Constructor()

    def main(self, code:str, filename="<main>"):
        codelns = code.split("\n")
        tree = None
        try:
            tree = self.parser.parse(code,filename)
        except lark.exceptions.UnexpectedCharacters as e:
            line = e.line -1 if e.line > 0 else -1
            col = e.column -1 if e.column > 0 else -1
            msg = "unexpected character at line"
            match e.char:
                case "{":
                    msg = "unmatched braces"
                case "\"":
                    msg = "unmatched quote"
                case "'":
                    msg = "unmatched quote"
                case "\n":
                    msg = "unexpected line break"
            print(color.fg.MAGENTA + f"{msg} {line+1} char {col+1}")
            print(color.RESET + "  "+codelns[line])
            print(color.fg.RED + "  "+" "*(col)+"^")
            return None
        except lark.exceptions.UnexpectedEOF as e:
            line = e.line -1 if e.line > 0 else -1
            col = e.column -1 if e.column > 0 else -1
            msg = "unexpected end of file"
            print(color.fg.MAGENTA + f"{msg}")
            print(color.RESET + "  "+codelns[line])
            print(color.fg.RED + "  "+" "*(col)+"^")
            print(color.fg.GRAY + f"There may be unmatched braces in the source")

        if tree is None:
            return

        print("\n".join([repr(item) for item in tree.children]))
        print("\n")
        try:
            out = self.constructor.main(tree,filename)
            print("\n".join(out))
        except parser.ParseErr as e:
            print(f"File {filename} line {e.line+1} char {e.col}")
            print(color.fg.MAGENTA + e.msg.capitalize())
            print(color.RESET + "  " + codelns[e.line])
            print(color.fg.RED + "  " + " "*e.col+"^"*(e.colend-e.col if e.col < e.colend else 1))
            print(color.fg.GRAY + e.hint.capitalize())
            return None
        #return out

def test():
    test = open("main.mi").read()

    assembler = Assembler()
    out = assembler.main(test)
    if out:
        with open("main.asm","wb") as file:
            file.write(out)

def main():
    argparser = argparse.ArgumentParser()

    argparser.add_argument("source",help="source assembly")
    argparser.add_argument("--output","-o",nargs="?",help="output file",default=None)

    args = argparser.parse_args()

    source:str = args.source
    dest = args.output

    if dest is None:
        dest = ".".join(source.split(".")[:-1]) + ".bin"

    if not os.path.isfile(source):
        sys.exit(f"")

    code = open(source).read()

    assembler = Assembler()
    out = assembler.main(code,source)
    if out:
        with open(dest,"wb") as file:
            file.write(out)
    else:
        sys.exit(1)

if __name__ == "__main__":
    test()
