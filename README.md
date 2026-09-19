# computer-architecture


Learn how a processor represents numbers, stores values, and performs instructions.
Start small: **C describes a task; assembly exposes processor instructions.** C also
specifies detailed behavior, and a compiler may optimize or reorder the instructions.

This repository contains working Python models, two toy assembly programs, a C
example, exercises, and automated checks. Python 3.9+ is sufficient; no packages
or GPU are required. Run all commands from this folder.

## Start here

```bash
python3 -m archlab.bits
python3 -m archlab.cpu programs/add.asm --trace
python3 -m unittest discover -s tests -v
```

The addition program finishes with `R0=12` and `memory[16]=12`. The trace shows the
program counter (PC), executed instruction, and register values after each step.

## Learning sequence

| Tier | Question | Run |
| --- | --- | --- |
| [1: Bits](tiers/tier-1/README.md) | How can the same bits mean different numbers? | `python3 -m archlab.bits` |
| [2: Logic and ALU](tiers/tier-2/README.md) | How do bit operations add numbers? | `python3 -m archlab.alu` |
| [3: Registers and memory](tiers/tier-3/README.md) | Where are values stored and copied? | `python3 -m archlab.memory` |
| [4: Instructions and CPU](tiers/tier-4/README.md) | How does a processor execute a program? | `python3 -m archlab.cpu programs/sum.asm --trace` |
| [5: Cache](tiers/tier-5/README.md) | Why does access order affect memory cost? | `python3 -m archlab.cache` |

## What is being simulated?

Physical processors use circuits to maintain state and transform electrical signals.
These Python models represent state with numbers and lists. They run on your actual
computer; they do not create transistors or model electrical behavior.

The teaching CPU has four 8-bit registers, 256 bytes of data memory, an instruction
index as its PC, and a separate list of decoded instructions. Assembly is parsed into
that list, not encoded into executable machine-code bytes. It is not x86 or ARM,
not cycle accurate, and has no operating system, pipeline, or cache integration.
The cache is a separate experiment. Instruction counts are not hardware clock cycles.

## C and assembly

Read [the C example](examples/add.c) alongside [the toy assembly](programs/add.asm).
Both express addition, but the toy assembly cannot be run directly on a real CPU.
With an optional C compiler installed, you can generate your machine's real assembly:

```bash
cc -O0 -S examples/add.c -o /tmp/add.s
cc examples/add.c -o /tmp/arch-add
/tmp/arch-add
```

Output syntax and instructions depend on your compiler and CPU. The Python lessons
work without a C compiler.

## Exercises and applications

Complete each tier's exercise before moving on. For engineering applications,
think of memory as storing a mesh, matrix, or model weights: how those values are
accessed affects performance. This repository teaches the foundations, not an FEA
solver or an inference benchmark.

## Put this project on GitHub

This download contains source files, not a hosted GitHub repository. After extracting,
create an empty repository named `intro-to-computer-architecture` on GitHub. From this
project folder, run the following, replacing YOUR_USERNAME:

```bash
git init
git add .
git commit -m "Add computer architecture learning labs"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/intro-to-computer-architecture.git
git push -u origin main
```

## Possible later extensions

These are future work, not implemented folders: binary instruction encoding,
a pipelined CPU with hazards, set-associative caches, virtual memory, compiled
matrix benchmarks, and GPU memory experiments.
