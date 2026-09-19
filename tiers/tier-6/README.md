# Tier 6 — Compiler principles

**A compiler translates a calculation into instructions the processor can execute.**
This lab takes a small expression language through parsing, an intermediate
representation (IR), optimization, and assembly generation. The assembled result
runs on the same teaching CPU from Tier 4. Python 3.9+ is sufficient.

## Start with the familiar work order

Run from the repository root:

```bash
python3 -m archlab.compiler examples/compiler/work_order.ac --set 20=12 --set 21=7 --set 22=5 --compare --show-ir
```

The source is:

```python
setup = load(20)
cycle = load(21)
quantity = load(22)
unused = (9 + 3) * 2
output = setup + cycle * quantity + 0
```

`load(20)` means read a byte from simulated memory address 20. The command's
`--set 20=12` places 12 there before execution; initialization is not part of
compiled program execution. Unspecified input memory starts at zero.
`output` names the result, which the compiler writes to memory address 16.

| Version | Result | Executed instructions | Data bytes read | Data bytes written |
| --- | ---: | ---: | ---: | ---: |
| Unoptimized | 47 | 60 | 14 | 13 |
| Optimized | 47 | 33 | 8 | 6 |

The optimized calculation still uses runtime inputs. Change quantity with
`--set 22=6` and the result becomes 54 without editing source code.

## What the compiler does

| Stage | Implemented behavior |
| --- | --- |
| Parsing | Python's standard AST parser supplies a syntax tree; our frontend accepts only this lab's small language |
| Semantic checks | Reject undefined variables, invalid literals/addresses, and unsupported expressions |
| Lowering to IR | Give each intermediate value a name such as `v0`; assignments refer to those values |
| Constant folding | Calculate constant expressions before CPU execution, with the same byte wrapping rules |
| Algebraic simplification | Remove addition by zero and multiplication by one; replace multiplication by zero |
| Common subexpression elimination | Reuse identical computations, including commuted integer addition/multiplication |
| Dead code elimination | Remove calculations that do not contribute to the final `output` |
| Assembly generation | Translate each IR operation to our CPU's instructions |
| Execution and measurement | Run that assembly and count executed instructions and data LOAD/STORE bytes |

These are compiler transformations, not text substitutions. For example, the
work-order optimization removes the entire unused dependency chain and the `+ 0`.
It cannot fold `cycle * quantity`, because their values arrive at runtime.

## Inspect each stage

```bash
python3 -m archlab.compiler examples/compiler/constants.ac --compare --show-ir --show-asm --emit-dir build/constants
python3 -m archlab.cpu build/constants/optimized.asm --trace
```

The constants example folds to one IR value, 47. The deliberately simple backend
still stores that value in scratch memory and reloads it to produce the output:
5 instructions versus 33 before optimization. An additional backend optimization
could remove those unnecessary moves; that is a future experiment.

Saved `.ir` and `.asm` files are ordinary text. The included
[generated work-order files](../../examples/compiler/generated/work-order/)
show both versions. The work-order assembly requires input memory to be populated;
use the compiler command with `--set` to run it with inputs. The CPU CLI alone
starts data memory at zero.

## Multiplication becomes a loop

Our CPU has no native `MUL`. The backend emits repeated addition, a counter, and
conditional branches. `JMP label` is an unconditional jump and is now supported
by the CPU. The generated loop handles a zero multiplier without entering it.
Loop cost depends on the multiplier; instruction counts are not CPU cycle counts.

## Reuse and a small model calculation

```bash
python3 -m archlab.compiler examples/compiler/reuse.ac --set 20=7 --set 21=5 --compare
python3 -m archlab.compiler examples/compiler/dot_product.ac --set 20=2 --set 21=3 --set 22=4 --set 23=5 --set 24=1 --compare
```

The reuse example computes `a*b + a*b`. The optimizer calculates the product
once, reducing execution from 51 to 31 instructions for these inputs; both return
70. The dot product is `x0*w0 + x1*w1 + bias`: `2*4 + 3*5 + 1 = 24`.
This is a small integer analogue of a neural-network calculation. It is not a
transformer or a GPU compiler. The connection to LLM runtimes is the translation
from expressions and dependencies to executable operations and memory accesses.

## Defined semantics and measurement boundary

- Values are unsigned eight-bit integers. Every addition and multiplication wraps
  modulo 256. For example, `250 + 7*5` returns 29 in both versions.
- Source syntax supports single-name assignments, parentheses, literals 0..255,
  names, `+`, `*`, and `load(literal_address)`. `#` introduces a comment.
  Reassignment is allowed; a use refers to the most recent preceding assignment.
- A variable named `output` is required; its final assigned value is the result.
  Source conditionals, loops, calls other than `load`, arrays, floats, subtraction,
  and division are not part of this language. The source is parsed, never eval'd.
- Input memory is 0..127; output uses address 16. Scratch memory is 128..255.
  Each retained IR value gets one scratch byte, so each emitted version permits
  at most 128 IR values. `--compare` must be able to emit both versions.
- Inputs stay unchanged until the final store to address 16. There are no volatile
  reads or device registers, so repeated loads can be shared and unused loads
  removed. Those transformations would need different rules for device I/O.
- The backend uses fixed scratch registers and one memory home per value. It
  does not implement register allocation, scheduling, or reuse of scratch slots.
- Byte counters count executed data `LOAD`/`STORE` instructions, one byte each,
  including scratch traffic. They exclude input initialization, result inspection,
  instruction fetching, and host Python memory. There is no cache in this path.
  These numbers are not GPU/HBM measurements and do not predict real speedups.
- Quantization/batching illustrations from the conversation are not implemented
  in this integer compiler. Floating-point rewrites require separate numerical
  rules; transformations valid for byte integers do not automatically apply.

## Exercise

Add an unused calculation, then compare execution. It should disappear only in
the optimized version. Next replace a literal with `load(25)` and supply it with
`--set 25=...`: observe which operations can no longer be folded at compile time.

## Verify

```bash
python3 -m unittest discover -s tests -v
```

Tests compare both compiled versions with independent arithmetic expectations,
including randomized programs, wraparound, zero multiplication, reassignment,
load reuse, invalid source, memory limits, and export/run behavior.
