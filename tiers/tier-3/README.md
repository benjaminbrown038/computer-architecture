# Tier 3 — Registers and memory

Run from the repository root:

```bash
python3 -m archlab.memory
```

A register is a small storage location inside a processor. Memory stores a larger
collection of values addressed by location. This model treats each memory address
as one byte and each register as eight bits.

Loading copies a memory value into a register. It does not create a live link.
Expected: `Memory[16]=99, register=42` after the original 42 is loaded and memory
is subsequently changed.

Exercise: write the register back to address 17. Predict both memory locations.
Answer: address 16 remains 99; address 17 becomes 42.

The model has no clock, memory latency, pointers, or cache coherence protocol.
