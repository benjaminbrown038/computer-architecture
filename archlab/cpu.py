"""Interpreter for an educational assembly language; not x86 or ARM."""
import argparse
from pathlib import Path
from archlab.alu import add
from archlab.memory import Memory

ARITY = {"MOV": 2, "ADD": 2, "DEC": 1, "LOAD": 2, "STORE": 2,
         "JNZ": 2, "HALT": 0, "CALL": 1, "RET": 0, "JMP": 1}


def assemble(source):
    labels, instructions = {}, []
    for number, line in enumerate(source.splitlines(), 1):
        line = line.split(";", 1)[0].strip()
        if not line:
            continue
        if ":" in line:
            label, line = (part.strip() for part in line.split(":", 1))
            if not label.isidentifier() or label in labels:
                raise ValueError(f"line {number}: invalid or duplicate label")
            labels[label] = len(instructions)
        if line:
            tokens = line.replace(",", " ").split()
            op, args = tokens[0].upper(), tokens[1:]
            if op not in ARITY or len(args) != ARITY[op]:
                raise ValueError(f"line {number}: invalid instruction")
            instructions.append((op, args))
    program = []
    for op, args in instructions:
        resolved = []
        for i, token in enumerate(args):
            if op in ("CALL", "JMP"):
                if token not in labels or labels[token] >= len(instructions):
                    raise ValueError(f"invalid jump/call label: {token}")
                resolved.append(labels[token])
            elif i == 0 or (op == "ADD" and i == 1):
                if token.upper() not in ("R0", "R1", "R2", "R3"):
                    raise ValueError(f"invalid register: {token}")
                resolved.append(int(token[1:]))
            elif op == "JNZ":
                if token not in labels or labels[token] >= len(instructions):
                    raise ValueError(f"invalid branch label: {token}")
                resolved.append(labels[token])
            else:
                value = int(token, 0)
                if op in ("LOAD", "STORE") and not 0 <= value < 256:
                    raise ValueError("memory address must be 0..255")
                resolved.append(value)
        program.append((op, resolved))
    return program


class CPU:
    def __init__(self, program):
        self.program = program
        self.registers = [0] * 4
        self.memory = Memory()
        self.pc = 0
        self.steps = 0
        self.halted = False
        self.return_stack = []
        self.stack_limit = 64

    def step(self):
        if self.halted:
            raise RuntimeError("CPU already halted")
        if not 0 <= self.pc < len(self.program):
            raise RuntimeError("program ended without HALT")
        old_pc = self.pc
        op, args = self.program[self.pc]
        if op == "RET" and not self.return_stack:
            raise RuntimeError("RET with empty return stack")
        if op == "CALL" and len(self.return_stack) >= self.stack_limit:
            raise RuntimeError("return stack overflow")
        self.pc += 1
        r = self.registers
        if op == "MOV":
            r[args[0]] = args[1] & 255
        elif op == "ADD":
            r[args[0]], _ = add(r[args[0]], r[args[1]])
        elif op == "DEC":
            r[args[0]] = (r[args[0]] - 1) & 255
        elif op == "LOAD":
            r[args[0]] = self.memory.read(args[1])
        elif op == "STORE":
            self.memory.write(args[1], r[args[0]])
        elif op == "JNZ":
            if r[args[0]] != 0:
                self.pc = args[1]
        elif op == "JMP":
            self.pc = args[0]
        elif op == "CALL":
            self.return_stack.append(self.pc)
            self.pc = args[0]
        elif op == "RET":
            self.pc = self.return_stack.pop()
        elif op == "HALT":
            self.halted = True
        self.steps += 1
        return f"PC={old_pc:02} {op:5} {str(args):10} -> R={r} next_PC={self.pc} stack={self.return_stack}"

    def run(self, trace=False, limit=10000):
        while not self.halted:
            if self.steps >= limit:
                raise RuntimeError("instruction limit reached; possible infinite loop")
            line = self.step()
            if trace:
                print(line)
        return self


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", type=Path)
    parser.add_argument("--trace", action="store_true")
    parser.add_argument("--watch", nargs="+", type=int, default=[16],
                        help="memory addresses to print after execution (0..255)")
    args = parser.parse_args()
    if any(not 0 <= address < 256 for address in args.watch):
        parser.error("--watch addresses must be 0..255")
    cpu = CPU(assemble(args.program.read_text())).run(args.trace)
    print(f"HALTED after {cpu.steps} instructions; registers={cpu.registers}")
    for address in args.watch:
        print(f"memory[{address}]={cpu.memory.read(address)}")


if __name__ == "__main__":
    main()
