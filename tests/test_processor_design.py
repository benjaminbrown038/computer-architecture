import unittest
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from archlab.cache import Cache
from archlab.cpu import CPU, assemble, main
from archlab.memory import Memory
from archlab.memory_system import MemorySystem

ROOT = Path(__file__).resolve().parents[1]


class ProcessorDesignTests(unittest.TestCase):
    def program(self, name, **config):
        return CPU(assemble((ROOT / "programs" / name).read_text()), **config).run()

    def test_multiply_matches_repeated_addition(self):
        old = (ROOT / 'programs/work-order-time.asm').read_text()
        new = (ROOT / 'programs/work-order-mul.asm').read_text()
        for quantity in (0, 1, 5, 35, 255):
            expected = (12 + 7 * quantity) % 256
            for source in (old, new):
                cpu = CPU(assemble(source.replace('MOV R3, 5', f'MOV R3, {quantity}'))).run()
                self.assertEqual(cpu.memory.read(16), expected)
        before = CPU(assemble(old)).run()
        after = CPU(assemble(new)).run()
        self.assertEqual((before.steps, after.steps), (27, 13))
        self.assertEqual((before.cycles, after.cycles), (167, 155))
        # Fewer instructions do not guarantee fewer cycles: vary MUL's cost.
        expensive = CPU(assemble(new), mul_cycles=50).run()
        self.assertGreater(expensive.cycles, before.cycles)

    def test_width_and_little_endian_round_trip(self):
        for bits, result, raw in ((8, 88, [88]), (16, 600, [88, 2]),
                                  (32, 600, [88, 2, 0, 0])):
            cpu = self.program('register-width.asm', register_bits=bits)
            self.assertEqual(cpu.registers[2], result)
            self.assertEqual(list(cpu.memory.data[16:16 + bits // 8]), raw)
            self.assertEqual(cpu.stats()['read_bytes'], bits // 8)
            self.assertEqual(cpu.stats()['written_bytes'], bits // 8)
        source = 'MOV R0, 0x12345678\nSTOREW R0, 252\nLOADW R1, 252\nHALT'
        cpu = CPU(assemble(source), register_bits=32).run()
        self.assertEqual(list(cpu.memory.data[252:]), [0x78, 0x56, 0x34, 0x12])
        self.assertEqual(cpu.registers[1], 0x12345678)

    def test_width_wrap_and_byte_instructions(self):
        for bits in (8, 16, 32):
            source = ('MOV R0, -1\nMOV R1, 1\nADD R0, R1\n'
                      'DEC R0\nMOV R2, 2\nMUL R0, R2\n'
                      'STORE R0, 255\nLOAD R3, 255\nHALT')
            cpu = CPU(assemble(source), register_bits=bits).run()
            self.assertEqual(cpu.registers[0], (1 << bits) - 2)
            self.assertEqual(cpu.registers[3], 254)
            self.assertEqual((cpu.stats()['read_bytes'], cpu.stats()['written_bytes']), (1, 1))

    def test_reuse_and_memory_accounting(self):
        uncached = self.program('cache-reuse.asm')
        cached = self.program('cache-reuse.asm', cache=Cache())
        self.assertEqual(uncached.memory.data, cached.memory.data)
        self.assertEqual(cached.memory.read(16), 28)
        # 22 execution + 6 lookups + 20*(one read fill + two writes) = 88.
        self.assertEqual((uncached.cycles, cached.cycles), (142, 88))
        self.assertEqual(cached.stats(), {
            'instructions': 22, 'modeled_cycles': 88, 'loads': 4, 'stores': 2,
            'read_bytes': 4, 'written_bytes': 2, 'backing_read_bytes': 4,
            'backing_written_bytes': 2, 'cache_hits': 3, 'cache_misses': 3})
        # Inspecting raw memory is outside the measurement boundary.
        before = cached.stats()
        cached.memory.read(16)
        self.assertEqual(cached.stats(), before)

    def test_conflict_and_capacity(self):
        for lines, cycles, hits, misses, backing in ((None, 252, 0, 0, 8),
                                                    (4, 263, 0, 11, 32),
                                                    (8, 143, 6, 5, 8)):
            cpu = self.program('cache-conflict.asm', cache=Cache(lines) if lines else None)
            self.assertEqual(cpu.memory.read(32), 20)
            self.assertEqual(cpu.cycles, cycles)
            self.assertEqual((cpu.stats()['cache_hits'], cpu.stats()['cache_misses']), (hits, misses))
            self.assertEqual(cpu.stats()['backing_read_bytes'], backing)

    def test_store_hit_updates_value_and_miss_does_not_evict(self):
        cache = Cache()
        memory = MemorySystem(Memory(), cache)
        memory.memory.write(0, 42)  # Preload is excluded from instruction counters.
        self.assertEqual(memory.read(0), 42)  # Miss, fetch bytes 0..3.
        memory.write(0, 99)  # Hit; write-through to backing memory.
        self.assertEqual(memory.read(0), 99)
        memory.write(16, 7)  # Conflicting write miss must not evict block 0.
        self.assertEqual(memory.read(0), 99)
        self.assertEqual((cache.hits, cache.misses), (3, 2))
        self.assertEqual((memory.backing_read_bytes, memory.backing_written_bytes), (4, 2))
        self.assertEqual(memory.memory.read(16), 7)

    def test_word_crosses_block_boundary(self):
        cpu = CPU(assemble('LOADW R0, 3\nLOADW R1, 3\nHALT'),
                  register_bits=16, cache=Cache())
        cpu.memory.write(3, 0x34)
        cpu.memory.write(4, 0x12)
        trace = cpu.step()
        self.assertIn('cache H=0 M=2', trace)
        cpu.run()
        self.assertEqual(cpu.registers[:2], [0x1234, 0x1234])
        self.assertEqual((cpu.stats()['cache_hits'], cpu.stats()['cache_misses']), (2, 2))
        self.assertEqual(cpu.stats()['backing_read_bytes'], 8)
        self.assertEqual(cpu.cycles, 47)  # 3 execution + 4 lookups + 2 fills.

    def test_word_store_and_partial_final_block(self):
        memory = MemorySystem(Memory(), Cache(block_size=3))
        memory.read(255)
        self.assertEqual(memory.backing_read_bytes, 1)  # Only one byte exists in last block.
        memory.write(2, 0x1234, size=2)
        self.assertEqual(memory.last_access.misses, 2)
        self.assertEqual(memory.last_access.cycles, 22)  # Two lookups, one backing write.
        self.assertEqual(list(memory.memory.data[2:4]), [0x34, 0x12])

    def test_invalid_word_access_has_no_partial_effect(self):
        for op in ('LOADW', 'STOREW'):
            cpu = CPU(assemble(f'{op} R0, 255\nHALT'), register_bits=16, cache=Cache())
            cpu.registers[0] = 600
            before = cpu.stats()
            with self.assertRaisesRegex(ValueError, 'out of range'):
                cpu.step()
            self.assertEqual(cpu.stats(), before)
            self.assertEqual(cpu.memory.data, bytearray(256))
            self.assertEqual(cpu.registers[0], 600)
            self.assertEqual(cpu.pc, 0)

    def test_cost_configuration_and_errors(self):
        cpu = CPU(assemble('LOAD R0, 0\nLOAD R1, 1\nHALT'), cache=Cache(),
                  memory_cycles=7, cache_cycles=2).run()
        self.assertEqual(cpu.cycles, 14)  # 3 instructions + 4 lookup + 7 fill.
        for kwargs in ({'register_bits': 7}, {'mul_cycles': 0},
                       {'memory_cycles': -1}, {'cache_cycles': 0}):
            with self.assertRaises(ValueError):
                CPU(assemble('HALT'), **kwargs)
        for source in ('MUL R0, 2', 'MUL R4, R1', 'LOADW R0, 256'):
            with self.assertRaises(ValueError):
                assemble(source)

    def test_cli_stats_and_error_message(self):
        out = StringIO()
        argv = ['cpu', str(ROOT / 'programs/register-width.asm'), '--register-bits', '16',
                '--cache', '--trace', '--stats', '--watch', '16', '17']
        with patch('sys.argv', argv), redirect_stdout(out):
            main()
        self.assertIn('registers=[600, 3, 600, 0]', out.getvalue())
        self.assertIn('read=2 B; written=2 B', out.getvalue())
        self.assertIn('MODELED CYCLES:', out.getvalue())
        err = StringIO()
        with patch('sys.argv', argv + ['--cache-lines', '0']), redirect_stderr(err):
            with self.assertRaises(SystemExit):
                main()
        self.assertIn('cache dimensions', err.getvalue())


if __name__ == '__main__':
    unittest.main()
