# Tier 7 — Design and measure a processor

Run from the repository root, with Python 3.9+ and no third-party packages:

```bash
python3 -m archlab.experiments
```

This executes real programs in the teaching interpreter, changing one design
choice at a time. It compares a multiply instruction, register widths, cache
reuse, and cache conflicts. It measures simulated data traffic and sums assumed
costs. It does not benchmark your host processor or simulate electrical signals.

## How hardware executes an instruction

Consider `ADD R0, R1`. An actual processor receives a machine-code bit pattern.
Instruction-decoding circuitry produces control signals; selected register
values reach arithmetic circuitry; the resulting bit pattern is written back
into a register. Clocked storage captures results at defined times. Modern
processors can overlap and reorganize internal work while preserving the
required visible behavior. One instruction is not necessarily one clock cycle.

| Processor action | Our representation |
| --- | --- |
| Fetch the next instruction | `self.program[self.pc]`, a previously decoded Python tuple |
| Decode its operation and operands | The opcode branches in `CPU.step()` |
| Read selected registers | Index the `self.registers` list |
| Add bits and carry between positions | `archlab.alu.add()` and `full_adder()` |
| Multiply | Python multiplication plus a register-width mask; no multiplier circuit is simulated |
| Write back the result | Assign the result into the register list |
| Select the next instruction | Advance or replace `self.pc` |
| Access memory | `MemorySystem`, with optional cache tags and transfer accounting |

The entire instruction completes during one `step()` call. Cycles are accumulated
after its effects; the simulator does not advance through individual hardware
stages or delay when a result becomes available. Registers and addresses in this
model do not identify your Mac's actual registers or physical memory addresses.

## 1. Add an instruction: MUL

```bash
python3 -m archlab.cpu programs/work-order-time.asm --stats
python3 -m archlab.cpu programs/work-order-mul.asm --stats --trace
```

Both compute `12 + 7 * 5 = 47`, including input initialization and output storage.

| Version | Result | Instructions | Data read / written | Modeled cycles |
| --- | ---: | ---: | ---: | ---: |
| Repeated addition | 47 | 27 | 3 B / 4 B | 167 |
| `MUL` instruction | 47 | 13 | 3 B / 4 B | 155 |

`MUL R1, R2` sets `R1 = (R1 * R2) mod 2^register_bits`. The other register
is unchanged. Zero multiplication works without a loop. The example costs three
cycles for `MUL` instead of the one-cycle execution cost of other instructions.
Both programs have the same seven uncached data-memory transfers at 20 cycles
each: the instruction reduction does not remove this memory cost.

```bash
python3 -m archlab.cpu programs/work-order-mul.asm --mul-cycles 50 --stats
```

With that changed assumption, the shorter program takes 202 modeled cycles,
more than the repeated-addition version. Instruction count alone is not time.
The Tier 6 compiler remains an eight-bit compiler targeting the original subset
without `MUL`; the new instruction is demonstrated by the hand-written assembly.

## 2. Change register width without changing byte addresses

```bash
python3 -m archlab.cpu programs/register-width.asm --register-bits 8 --stats
python3 -m archlab.cpu programs/register-width.asm --register-bits 16 --stats --watch 16 17
python3 -m archlab.cpu programs/register-width.asm --register-bits 32 --stats --watch 16 17 18 19
```

The program multiplies 200 by 3, stores the result, and reloads it into R2.

| Register bits | Result in R2 | Bytes at address 16 onward | Read / written |
| --- | ---: | --- | ---: |
| 8 | 88 | `88` | 1 B / 1 B |
| 16 | 600 | `88, 2` | 2 B / 2 B |
| 32 | 600 | `88, 2, 0, 0` | 4 B / 4 B |

An eight-bit value wraps because `600 mod 256 = 88`. The full 16-bit value is
`88 + 2 * 256 = 600`. Little-endian means the least significant byte comes first.
Memory still contains 256 individually addressed bytes regardless of register width.

- `MOV`, `ADD`, `MUL`, and `DEC` wrap to 8, 16, or 32 bits.
- `LOAD` always reads one byte, producing a register value in 0..255.
- `STORE` always writes only the low eight bits of its source register.
- `LOADW` and `STOREW` transfer a full register: 1, 2, or 4 consecutive bytes.
- Word transfers may be unaligned. Every byte must be in 0..255; an invalid
  transfer fails before changing registers, PC, memory, or measurement counters.
- The PC remains an instruction index and the return stack remains separate.

Wider registers alone do not change byte operations. Use the explicit word
instructions to save or reload a larger value without truncation.

## 3. Connect a small cache

```bash
python3 -m archlab.cpu programs/cache-reuse.asm --stats
python3 -m archlab.cpu programs/cache-reuse.asm --cache --stats --trace
python3 -m archlab.cpu programs/cache-conflict.asm --cache --stats --watch 32
python3 -m archlab.cpu programs/cache-conflict.asm --cache --cache-lines 8 --stats --watch 32
```

Defaults are four direct-mapped lines of four bytes each: 16 bytes of modeled
capacity. Each run in the experiments starts with an empty cache. A read miss
fetches its block. Reads of that block can then hit until a conflicting read
replaces it. Tags model which blocks are resident; functional values come from
the single `Memory` object. No actual payload bytes are stored in `Cache`.

Stores use **write-through, no-write-allocate**: each store writes to backing
memory. A hit preserves the resident block; a miss neither allocates nor evicts
a line. There are no dirty lines, write buffers, or deferred writebacks.

| Program / cache | Result | Instructions | Hits / misses | Backing read / written | Modeled cycles |
| --- | ---: | ---: | ---: | ---: | ---: |
| Reuse / none | 28 | 22 | n/a | 4 B / 2 B | 142 |
| Reuse / 4 lines | 28 | 22 | 3 / 3 | 4 B / 2 B | 88 |
| Conflict / none | 20 | 32 | n/a | 8 B / 3 B | 252 |
| Conflict / 4 lines | 20 | 32 | 0 / 11 | 32 B / 3 B | 263 |
| Conflict / 8 lines | 20 | 32 | 6 / 5 | 8 B / 3 B | 143 |

Hits and misses include **both loads and stores**, one lookup per block touched
by an instruction. In the reuse program, the first load and both stores miss;
three later loads hit. Its cycles are `22 + 6 lookups + 20 * 3 transfers = 88`.
It fetches the same number of backing bytes as the uncached version, but in
one four-byte read rather than four one-byte reads. The transfer count matters
under this model's fixed per-transfer latency.

In the conflict program, addresses 0 and 16 both select line 0 in a four-line
cache. Every load replaces the previous block. Extra fetched bytes and lookup
cost make that cache worse than no cache. Eight lines give these two blocks
different positions. This is why merely adding a cache does not guarantee a gain.

## 4. Know exactly what the counters mean

| Counter | Included |
| --- | --- |
| Instructions | Every completed instruction, including `HALT`, branches and calls |
| Loads / stores | One per completed byte or word data-memory instruction |
| Data read / written | Bytes requested by those instructions |
| Backing read | Requested bytes when uncached; fetched blocks on cached read misses |
| Backing written | Every byte stored, with or without a cache |
| Cache hits / misses | One lookup per touched block, including store misses |
| Modeled cycles | Instruction execution costs plus data-memory costs, added serially |

Initialization performed by assembly instructions counts. Preloading with
`cpu.memory.write(...)` before running does not count. Inspection using
`cpu.memory.read(...)` or `--watch` does not count or warm the cache. The counters
exclude instruction fetching, host Python memory, and the abstract return stack.

For a word contained in one cache block there is one lookup. A word crossing
two blocks needs two lookups and may cause two fills. A block at the end of
memory fetches only existing bytes. Cache geometry need not use powers of two.

## 5. Change the timing assumptions

```bash
python3 -m archlab.cpu programs/cache-reuse.asm --cache --memory-cycles 40 --cache-cycles 2 --stats
```

The precise rules are:

- Execution costs one cycle for every instruction except `MUL`, which costs
  `--mul-cycles` (default 3) in total before any memory costs.
- An uncached byte or word load/store adds `--memory-cycles` (default 20)
  for its one backing-memory transfer.
- A cached load adds `--cache-cycles` (default 1) per touched block plus
  `--memory-cycles` for each block miss.
- A cached store adds `--cache-cycles` per touched block plus one
  `--memory-cycles` backing write for the entire instruction, hit or miss.
- Transfer cost is fixed regardless of byte count. This is a latency model;
  finite bus bandwidth and transfer-size-dependent cost are not modeled.
- Costs are positive integer cycles. All operations are blocking and serial;
  there is no pipelining, instruction cache, prefetching, speculation, coherence,
  multicore execution, or overlap between arithmetic and memory transfers.

`--trace` prints the instruction's added cycles and cumulative total. Memory
instructions also print address, byte count, value, cache lookups, and memory cost.
These are assumed costs, not clock-accurate traces or measured hardware timings.

## Python API and implementation locations

```python
from archlab.cache import Cache
from archlab.cpu import CPU, assemble

source = "LOAD R0, 20\nLOAD R1, 20\nADD R0, R1\nSTORE R0, 16\nHALT"
cpu = CPU(assemble(source), register_bits=16, cache=Cache(lines=4, block_size=4))
cpu.memory.write(20, 7)  # Preload before running; not an executed store.
cpu.run(trace=True)
print(cpu.memory.read(16))  # 14; inspection is not an executed load.
print(cpu.stats())
```

Pass a fresh `Cache` when comparing cold runs. The cache object's counters and
tags persist if you explicitly reuse it. `cpu.stats()` exposes those cache counters.

- `archlab/cpu.py`: assembler, instruction behavior, width, trace, CLI, cycle sum.
- `archlab/memory_system.py`: transfer spans, byte ordering, traffic and latency.
- `archlab/cache.py`: direct mapping, tags, hit/miss and allocation policy.
- `archlab/experiments.py`: execute the comparisons and print their measurements.
- `tests/test_processor_design.py`: semantic equivalence, wraparound, cache writes,
  conflicts, cross-block words, boundaries, accounting, and CLI checks.

## Next experiments

Change the cache block size with `--block-size`, then inspect backing bytes and
cycles together. Change `--mul-cycles` and find when the instruction-count gain
stops helping the work order. Change register width and compare byte versus word
stores. Each experiment changes an explicit rule and makes its consequences visible.
