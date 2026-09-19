# Tier 4 — Instructions and a tiny CPU

Run from the repository root:

```bash
python3 -m archlab.cpu programs/sum.asm --trace
```

The PC selects the next instruction. The CPU fetches it, determines its operation,
updates registers or memory, and selects the next PC. A branch can jump backward.

| Instruction | Meaning |
| --- | --- |
| `MOV R0, 5` | Put an immediate value into R0 (wrapped to eight bits) |
| `ADD R0, R1` | Add R1 to R0, retaining the low eight bits |
| `DEC R1` | Subtract one from R1, wrapping at zero |
| `LOAD R0, 16` | Copy memory byte 16 into R0 |
| `STORE R0, 16` | Copy R0 into memory byte 16 |
| `JNZ R1, loop` | Jump to label loop if R1 is not zero |
| `HALT` | Stop execution |

Registers are R0 through R3. Literals accept decimal and `0x` hexadecimal.
Comments begin with `;`. Labels are case-sensitive. Arithmetic flags from the ALU
are not stored in this CPU; JNZ examines a register directly.

Expected: the sum program executes 19 instructions, including HALT, and stores 15
at address 16. The displayed PC is an instruction index, not a byte address.

Exercise: change the initial R1 from 5 to 10. Predict the result and instruction
count before running. Answer: 55 and 34 instructions.

A missing HALT and a loop exceeding 10,000 executed instructions raise errors.
