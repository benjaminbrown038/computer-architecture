import random
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from unittest.mock import patch

from archlab.compiler import CompileError, compile_source, emit_assembly, execute, lower, optimize, main
from archlab.cpu import CPU, assemble

ROOT = Path(__file__).resolve().parents[1]


class CompilerTests(unittest.TestCase):
    def both(self, source, inputs, expected):
        before = execute(compile_source(source, optimized=False), inputs)
        after = execute(compile_source(source), inputs)
        self.assertEqual(before['result'], expected)
        self.assertEqual(after['result'], expected)
        return before, after

    def test_runtime_work_order(self):
        source = (ROOT / 'examples/compiler/work_order.ac').read_text()
        before, after = self.both(source, {20: 12, 21: 7, 22: 5}, 47)
        self.assertLess(after['instructions'], before['instructions'])
        self.assertLess(after['read_bytes'] + after['written_bytes'],
                        before['read_bytes'] + before['written_bytes'])
        self.both(source, {20: 12, 21: 7, 22: 0}, 12)

    def test_constant_folding_and_precedence(self):
        source = 'output = 250 + 7 * 5'
        self.both(source, {}, 29)
        folded = optimize(lower(source))
        self.assertEqual(len(folded.instructions), 1)
        self.assertEqual(folded.instructions[0].args, (29,))
        self.both('output = (250 + 7) * 5', {}, 5)

    def test_reuse_and_dead_code(self):
        source = 'a = load(20)\nb = load(21)\ndead = 19 * 12\noutput = a * b + b * a'
        ir = optimize(lower(source))
        self.assertEqual(sum(i.op == 'mul' for i in ir.instructions), 1)
        self.both(source, {20: 7, 21: 5}, 70)

    def test_identity_and_reassignment(self):
        self.both('a = load(20)\na = a + 1\noutput = a * 1 + 0', {20: 255}, 0)
        self.both('output = load(20) * 0\ndead = load(21)', {20: 200}, 0)
        # Result address may also be an input: the only store to it is at the end.
        self.both('a = load(16)\noutput = a + load(16)', {16: 130}, 4)

    def test_randomized_expression_programs(self):
        rng = random.Random(2026)
        for _ in range(40):
            inputs = {20: rng.randrange(256), 21: rng.randrange(256)}
            lines = ['a = load(20)', 'b = load(21)']
            values = {'a': inputs[20], 'b': inputs[21]}
            for i in range(6):
                left = rng.choice(list(values))
                right = rng.choice(list(values))
                op = rng.choice(['+', '*'])
                name = f'n{i}'
                lines.append(f'{name} = {left} {op} {right}')
                values[name] = ((values[left] + values[right]) if op == '+'
                                else (values[left] * values[right])) & 255
            lines.append('output = n5')
            self.both('\n'.join(lines), inputs, values['n5'])

    def test_source_diagnostics(self):
        invalid = ['output = missing', 'output = 256', 'output = -1',
                   'output = True', 'output = 1.5', 'output = load(128)',
                   'output = load(20, 21)', 'output = load(address=20)',
                   'output = 2 / 1', 'output = print(1)', 'import os',
                   'a = 1', 'load = 3\noutput = load', 'a = b = 2\noutput = a',
                   'output = [1, 2]', 'output = (']
        for source in invalid:
            with self.subTest(source=source), self.assertRaises(CompileError):
                compile_source(source)

    def test_scratch_limit_and_inputs(self):
        source = '\n'.join(f'x{i} = {i % 256}' for i in range(129)) + '\noutput = x128'
        with self.assertRaisesRegex(CompileError, 'scratch'):
            compile_source(source, optimized=False)
        self.assertEqual(execute(compile_source(source))['result'], 128)
        for inputs in ({128: 1}, {20: 256}):
            with self.assertRaises(ValueError):
                execute(compile_source('output = 1'), inputs)

    def test_jump_instruction(self):
        cpu = CPU(assemble('JMP done\nMOV R0, 99\ndone: HALT')).run()
        self.assertEqual(cpu.registers[0], 0)
        self.assertEqual(cpu.steps, 2)
        with self.assertRaises(ValueError):
            assemble('JMP missing')

    def test_cli_exports_and_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            argv = ['compiler', str(ROOT / 'examples/compiler/constants.ac'),
                    '--compare', '--show-ir', '--show-asm', '--emit-dir', tmp]
            out = StringIO()
            with patch('sys.argv', argv), redirect_stdout(out):
                main()
            self.assertIn('result=47', out.getvalue())
            for stem in ['optimized', 'unoptimized']:
                assembly = (Path(tmp) / f'{stem}.asm').read_text()
                self.assertEqual(execute(assembly)['result'], 47)
                self.assertTrue((Path(tmp) / f'{stem}.ir').read_text())
