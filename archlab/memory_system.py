"""Count instruction data traffic and model a blocking, single-level cache.

Memory remains the source of functional values. Cache tags model residency,
transfers, and costs; there is no second copy of the data. This is not a physical
timing prediction. Input initialization and inspection use Memory directly.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Access:
    operation: str
    address: int
    size: int
    value: int
    hits: int
    misses: int
    cycles: int
    cached: bool

    def describe(self):
        cache = f"cache H={self.hits} M={self.misses}" if self.cached else "uncached"
        return (f"{self.operation} [{self.address}] {self.size} B value={self.value}; "
                f"{cache}; memory_cycles={self.cycles}")


class MemorySystem:
    def __init__(self, memory, cache=None, memory_cycles=20, cache_cycles=1):
        for name, value in (("memory_cycles", memory_cycles), ("cache_cycles", cache_cycles)):
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        self.memory = memory
        self.cache = cache
        self.memory_cycles = memory_cycles
        self.cache_cycles = cache_cycles
        self.read_bytes = self.written_bytes = 0
        self.backing_read_bytes = self.backing_written_bytes = 0
        self.loads = self.stores = 0
        self.last_access = None

    def check(self, address, size):
        # Validate the whole span before modifying memory, cache, or counters.
        if type(address) is not int or type(size) is not int or size < 1:
            raise ValueError("address and positive transfer size must be integers")
        self.memory.check(address)
        self.memory.check(address + size - 1)

    def _cost(self, address, size, write):
        if self.cache is None:
            if not write:
                self.backing_read_bytes += size
            return self.memory_cycles, 0, 0
        cache = self.cache
        first = address // cache.block_size
        last = (address + size - 1) // cache.block_size
        hits = misses = cycles = 0
        # One lookup per touched block, even for a multibyte word transfer.
        for block in range(first, last + 1):
            start = block * cache.block_size
            hit = cache.access(start, write=write)
            hits += int(hit)
            misses += int(not hit)
            cycles += self.cache_cycles
            if not write and not hit:
                cycles += self.memory_cycles
                self.backing_read_bytes += min(cache.block_size, len(self.memory.data) - start)
        # Write-through, no-write-allocate: every store goes to backing memory,
        # hits leave residency intact, misses neither fetch nor replace a line.
        if write:
            cycles += self.memory_cycles
        return cycles, hits, misses

    def read(self, address, size=1):
        self.check(address, size)
        cycles, hits, misses = self._cost(address, size, write=False)
        value = sum(self.memory.read(address + i) << (8 * i) for i in range(size))
        self.loads += 1
        self.read_bytes += size
        self.last_access = Access("read", address, size, value, hits, misses,
                                  cycles, self.cache is not None)
        return value

    def write(self, address, value, size=1):
        self.check(address, size)
        value &= (1 << (8 * size)) - 1
        cycles, hits, misses = self._cost(address, size, write=True)
        for i in range(size):
            self.memory.write(address + i, value >> (8 * i))
        self.stores += 1
        self.written_bytes += size
        self.backing_written_bytes += size
        self.last_access = Access("write", address, size, value, hits, misses,
                                  cycles, self.cache is not None)
