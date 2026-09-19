"""A small uint8 expression compiler targeting the archlab teaching CPU.

Source: assignments, integer literals, names, +, *, and load(address).
The final value of `output` is written to memory[16]. No Python code is executed.
"""
import argparse
import ast
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Union

from archlab.cpu import CPU, assemble


class CompileError(ValueError):
    pass


@dataclass(frozen=True)
class Instruction:
    target: str
    op: str
    args: Tuple[Union[str, int], ...]


@dataclass(frozen=True)
class IR:
    instructions: Tuple[Instruction, ...]
    output: str

    def text(self):
        lines = [f"{i.target} = {i.op} " + ", ".join(map(str, i.args))
                 for i in self.instructions]
        return "\n".join(lines + [f"output {self.output}"]) + "\n"


def lower(source):
    """Parse with Python's AST parser, then validate a restricted language."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, RecursionError) as exc:
        raise CompileError(f"invalid source: {exc}") from exc
    instructions, names = [], {}

    def error(node, message):
        raise CompileError(f"line {getattr(node, 'lineno', '?')}: {message}")

    def emit(op, *args):
        target = f"v{len(instructions)}"
        instructions.append(Instruction(target, op, tuple(args)))
        return target

    def expression(node):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            if not 0 <= node.value <= 255:
                error(node, "literals must be integers in 0..255")
            return emit("const", node.value)
        if isinstance(node, ast.Name):
            if node.id not in names:
                error(node, f"undefined variable {node.id!r}")
            return names[node.id]
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mult)):
            a, b = expression(node.left), expression(node.right)
            return emit("add" if isinstance(node.op, ast.Add) else "mul", a, b)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "load" and len(node.args) == 1 and not node.keywords:
                address = node.args[0]
                if (isinstance(address, ast.Constant) and type(address.value) is int
                        and 0 <= address.value <= 127):
                    return emit("load", address.value)
                error(node, "load requires a literal address in 0..127")
        error(node, "supported expressions: integer, variable, +, *, load(address)")

    for statement in tree.body:
        if not (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)):
            error(statement, "only single-name assignments are supported")
        name = statement.targets[0].id
        if name == "load":
            error(statement, "load is a reserved name")
        names[name] = expression(statement.value)
    if "output" not in names:
        raise CompileError("assign the result to a variable named output")
    return IR(tuple(instructions), names["output"])


def optimize(ir):
    """Fold constants, simplify identities, reuse expressions, eliminate dead code.

    Loads are pure here: input memory is unchanged until the final output store.
    All arithmetic is modulo 256, including compile-time folding.
    """
    aliases, constants, seen, rewritten = {}, {}, {}, []
    for inst in ir.instructions:
        op, args = inst.op, inst.args
        if op in ("add", "mul"):
            a, b = (aliases[x] for x in args)
            args = (a, b)
            ca, cb = constants.get(a), constants.get(b)
            if ca is not None and cb is not None:
                value = ca + cb if op == "add" else ca * cb
                op, args = "const", (value & 255,)
            elif op == "mul" and (ca == 0 or cb == 0):
                op, args = "const", (0,)
            elif (op == "add" and ca == 0) or (op == "mul" and ca == 1):
                aliases[inst.target] = b
                continue
            elif (op == "add" and cb == 0) or (op == "mul" and cb == 1):
                aliases[inst.target] = a
                continue
            else:
                # Integer add/multiply commute under the defined uint8 semantics.
                args = tuple(sorted(args))
        key = (op, args)
        if key in seen:
            aliases[inst.target] = seen[key]
            continue
        aliases[inst.target] = inst.target
        seen[key] = inst.target
        if op == "const":
            constants[inst.target] = args[0]
        rewritten.append(Instruction(inst.target, op, args))
    output = aliases[ir.output]
    needed, live = {output}, []
    for inst in reversed(rewritten):
        if inst.target in needed:
            live.append(inst)
            if inst.op in ("add", "mul"):
                needed.update(inst.args)
    return IR(tuple(reversed(live)), output)


def emit_assembly(ir):
    """Give every IR value a memory home; R0/R1/R2 are scratch registers."""
    if len(ir.instructions) > 128:
        raise CompileError("more than 128 intermediate values: scratch memory exhausted")
    homes = {inst.target: 128 + index for index, inst in enumerate(ir.instructions)}
    lines = ["; Generated by archlab.compiler; uint8 arithmetic wraps modulo 256."]
    for index, inst in enumerate(ir.instructions):
        lines.append(f"; {inst.target} = {inst.op} {', '.join(map(str, inst.args))}")
        if inst.op == "const":
            lines.append(f"MOV R0, {inst.args[0]}")
        elif inst.op == "load":
            lines.append(f"LOAD R0, {inst.args[0]}")
        elif inst.op == "add":
            a, b = (homes[x] for x in inst.args)
            lines.extend([f"LOAD R0, {a}", f"LOAD R1, {b}", "ADD R0, R1"])
        elif inst.op == "mul":
            a, b = (homes[x] for x in inst.args)
            loop, done = f"mul_{index}", f"done_{index}"
            lines.extend([f"LOAD R1, {a}", f"LOAD R2, {b}", "MOV R0, 0",
                          f"JNZ R2, {loop}", f"JMP {done}", f"{loop}:",
                          "ADD R0, R1", "DEC R2", f"JNZ R2, {loop}", f"{done}:"])
        else:
            raise CompileError(f"unknown IR operation: {inst.op}")
        lines.append(f"STORE R0, {homes[inst.target]}")
    lines.extend([f"LOAD R0, {homes[ir.output]}", "STORE R0, 16", "HALT"])
    return "\n".join(lines) + "\n"


def compile_source(source, optimized=True):
    ir = lower(source)
    if optimized:
        ir = optimize(ir)
    return emit_assembly(ir)


def execute(assembly, inputs=None, limit=1000000):
    """Count simulated data LOAD/STORE bytes; exclude setup and inspection."""
    cpu = CPU(assemble(assembly))
    for address, value in (inputs or {}).items():
        if type(address) is not int or not 0 <= address <= 127:
            raise ValueError("input addresses must be integers in 0..127")
        if type(value) is not int or not 0 <= value <= 255:
            raise ValueError("input values must be integers in 0..255")
        cpu.memory.write(address, value)
    counts = Counter()
    while not cpu.halted:
        if cpu.steps >= limit:
            raise RuntimeError("instruction limit reached")
        counts[cpu.program[cpu.pc][0]] += 1
        cpu.step()
    return {"result": cpu.memory.read(16), "instructions": cpu.steps,
            "read_bytes": counts["LOAD"], "written_bytes": counts["STORE"]}


def input_pair(text):
    try:
        address, value = (int(part, 0) for part in text.split("="))
        if not (0 <= address <= 127 and 0 <= value <= 255):
            raise ValueError()
        return address, value
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use ADDRESS=VALUE; address 0..127, value 0..255") from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--set", action="append", type=input_pair, default=[], metavar="ADDRESS=VALUE")
    parser.add_argument("--compare", action="store_true", help="execute both versions")
    parser.add_argument("--no-opt", action="store_true", help="disable optimization")
    parser.add_argument("--show-ir", action="store_true")
    parser.add_argument("--show-asm", action="store_true")
    parser.add_argument("--emit-dir", type=Path, help="save before/after IR and assembly")
    args = parser.parse_args()
    if args.compare and args.no_opt:
        parser.error("choose --compare or --no-opt")
    try:
        original = lower(args.source.read_text())
        improved = optimize(original)
        versions = [("unoptimized", original), ("optimized", improved)]
        if args.emit_dir:
            args.emit_dir.mkdir(parents=True, exist_ok=True)
            for name, ir in versions:
                (args.emit_dir / f"{name}.ir").write_text(ir.text())
                (args.emit_dir / f"{name}.asm").write_text(emit_assembly(ir))
        selected = versions if args.compare else [versions[0 if args.no_opt else 1]]
        observed = []
        for name, ir in selected:
            assembly = emit_assembly(ir)
            result = execute(assembly, dict(args.set))
            observed.append(result["result"])
            print(f"{name}: result={result['result']}; IR values={len(ir.instructions)}; "
                  f"executed instructions={result['instructions']}; "
                  f"data read={result['read_bytes']} B; written={result['written_bytes']} B")
            if args.show_ir:
                print(ir.text(), end="")
            if args.show_asm:
                print(assembly, end="")
        if len(observed) == 2 and observed[0] != observed[1]:
            raise RuntimeError("optimization changed the result")
    except (OSError, ValueError, RuntimeError, RecursionError) as exc:
        parser.exit(1, f"compiler: {exc}\n")


if __name__ == "__main__":
    main()
