import unittest
from pathlib import Path
from archlab.bits import unsigned, signed
from archlab.alu import add
from archlab.memory import Memory
from archlab.cpu import CPU, assemble
from archlab.cache import Cache

ROOT = Path(__file__).resolve().parents[1]


class ArchitectureTests(unittest.TestCase):
    def test_all_eight_bit_additions(self):
        for a in range(256):
            for b in range(256):
                result, flags = add(a, b)
                self.assertEqual(result, (a + b) % 256)
                self.assertEqual(flags["carry"], a + b > 255)
                total = signed(a) + signed(b)
                self.assertEqual(flags["overflow"], not -128 <= total <= 127)
                self.assertEqual(flags["zero"], result == 0)

    def test_bits(self):
        self.assertEqual(unsigned(-1), 255)
        self.assertEqual(signed(128), -128)
        with self.assertRaises(ValueError):
            unsigned(0, 0)

    def test_programs(self):
        for filename, expected, steps in (("add.asm", 12, 5), ("sum.asm", 15, 19)):
            cpu = CPU(assemble((ROOT / "programs" / filename).read_text())).run()
            self.assertEqual(cpu.memory.read(16), expected)
            self.assertEqual(cpu.steps, steps)

    def test_load_and_wrap(self):
        cpu = CPU(assemble("MOV R2, 256\nDEC R2\nSTORE R2, 255\nLOAD R3, 255\nHALT")).run()
        self.assertEqual(cpu.registers[3], 255)

    def test_errors(self):
        for source in ("MOV R9, 1", "LOAD R0, -1", "JNZ R0, missing", "BAD", "x: HALT\nx: HALT"):
            with self.assertRaises(ValueError):
                assemble(source)
        with self.assertRaises(RuntimeError):
            CPU(assemble("MOV R0, 1")).run()
        with self.assertRaises(RuntimeError):
            CPU(assemble("MOV R0, 1\nx: JNZ R0, x")).run(limit=20)
        with self.assertRaises(ValueError):
            Memory().read(-1)

    def test_cache_patterns(self):
        for addresses, misses in ((range(32), 8), (list(range(8)) * 4, 2), ([0, 16] * 16, 32)):
            cache = Cache()
            for address in addresses:
                cache.read(address)
            self.assertEqual(cache.misses, misses)
        cache = Cache(lines=8)
        for address in [0, 16] * 16:
            cache.read(address)
        self.assertEqual(cache.misses, 2)


if __name__ == "__main__":
    unittest.main()
