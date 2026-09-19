# Tier 5 — Cache and memory access

Run from the repository root:

```bash
python3 -m archlab.cache
```

A cache retains recently accessed blocks. This experiment models only whether
an address would hit or miss in a direct-mapped cache: four lines, four bytes per
block, initially empty. It does not store data or implement writes.

$$
\text{block} = \left\lfloor \frac{\text{address}}{4} \right\rfloor,
\qquad \text{index} = \text{block} \bmod 4
$$

The tag is floor(block / 4). Different blocks with the same index evict one another.

| Access pattern | Hits | Misses | Modeled cycles |
| --- | --- | --- | --- |
| Addresses 0 through 31 | 24 | 8 | 192 |
| Addresses 0 through 7 repeated four times | 30 | 2 | 72 |
| Addresses 0 and 16 alternating 16 times | 0 | 32 | 672 |

The model assumes one cycle for every access plus 20 additional cycles per miss.
These numbers are illustrative costs, not measurements of your computer.

Exercise: change the cache to eight lines. Predict alternating 0 and 16.
Answer: two initial misses followed by 30 hits (72 modeled cycles).

Sequential matrix or model-weight access can benefit from locality, but real
performance also depends on cache size, prefetching, bandwidth, and parallelism.
