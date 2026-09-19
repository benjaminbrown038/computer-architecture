# Tier 1 — Bits and number representation

Run from the repository root:

```bash
python3 -m archlab.bits
```

A bit has two possible values: 0 and 1. An 8-bit group has 256 possible patterns.
The interpretation determines the number: `11111111` means unsigned 255 or signed
-1 in two's complement.

$$
u = \sum_{i=0}^{7} b_i 2^i
$$

For signed interpretation, use u when u < 128, otherwise u - 256.
The code masks values to eight bits; 256 becomes 0. This is a chosen model rule,
not a claim that Python integers overflow.

Expected example: input -1 produces bits `11111111`, unsigned 255, signed -1.

Exercise: predict the output for 130. Then call `signed(130)` to check it.
Answer: -126.
