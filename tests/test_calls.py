import unittest
from pathlib import Path
from archlab.cpu import CPU, assemble

ROOT = Path(__file__).resolve().parents[1]

class CallTests(unittest.TestCase):
    def test_two_jobs_and_returns(self):
        cpu = CPU(assemble((ROOT / "programs/two-jobs.asm").read_text()))
        calls = []
        while not cpu.halted:
            op = cpu.program[cpu.pc][0]
            cpu.step()
            if op in ("CALL", "RET"):
                calls.append(list(cpu.return_stack))
        self.assertEqual(calls, [[4], [], [9], []])
        self.assertEqual([cpu.memory.read(a) for a in (16, 17, 18)], [47, 20, 67])
        self.assertEqual(cpu.steps, 43)

    def test_nested_calls(self):
        cpu = CPU(assemble("CALL outer\nHALT\nouter: CALL inner\nDEC R0\nRET\ninner: MOV R0, 5\nRET")).run()
        self.assertEqual(cpu.registers[0], 4)
        self.assertEqual(cpu.return_stack, [])

    def test_stack_errors(self):
        cpu = CPU(assemble("RET"))
        with self.assertRaisesRegex(RuntimeError, "empty"):
            cpu.step()
        self.assertEqual(cpu.pc, 0)
        with self.assertRaisesRegex(RuntimeError, "overflow"):
            CPU(assemble("again: CALL again")).run()
        for source in ("CALL missing", "CALL end\nHALT\nend:"):
            with self.assertRaises(ValueError):
                assemble(source)

    def test_zero_quantity(self):
        source = (ROOT / "programs/two-jobs.asm").read_text().replace("MOV R2, 5", "MOV R2, 0")
        cpu = CPU(assemble(source)).run()
        self.assertEqual([cpu.memory.read(a) for a in (16, 17, 18)], [12, 20, 32])

    def test_single_job(self):
        cpu = CPU(assemble((ROOT / "programs/work-order-time.asm").read_text())).run()
        self.assertEqual(cpu.memory.read(16), 47)
        self.assertEqual(cpu.steps, 27)
