# Tier 2 — Logic and arithmetic

Run from the repository root:

```bash
python3 -m archlab.alu
```

An ALU is an arithmetic and logic unit. Here we implement its addition operation
using eight one-bit full adders connected by carry bits.

$$
s = a \oplus b \oplus c_{in}
$$

$$
c_{out} = (a \land b) \lor (c_{in} \land (a \oplus b))
$$

Carry indicates an unsigned result beyond eight bits. Signed overflow indicates
that the mathematical signed result cannot fit in -128 through 127. They differ:
255 + 1 has carry, while 127 + 1 has signed overflow.

Expected: 5 + 7 produces 12 with neither carry nor overflow.

Exercise: predict flags for 128 + 128, then check `add(128, 128)`.
Answer: result 0, carry true, overflow true, zero true.
