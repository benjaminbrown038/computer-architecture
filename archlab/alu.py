from archlab.bits import unsigned, signed


def full_adder(a, b, carry):
    """One-bit adder: inputs and outputs are each 0 or 1."""
    if any(x not in (0, 1) for x in (a, b, carry)):
        raise ValueError("full_adder accepts bits only")
    return a ^ b ^ carry, (a & b) | (carry & (a ^ b))


def add(a, b, width=8):
    a, b = unsigned(a, width), unsigned(b, width)
    result, carry = 0, 0
    for bit in range(width):
        out, carry = full_adder((a >> bit) & 1, (b >> bit) & 1, carry)
        result |= out << bit
    sign = 1 << (width - 1)
    overflow = bool((~(a ^ b) & (a ^ result)) & sign)
    return result, {"carry": bool(carry), "overflow": overflow, "zero": result == 0}


def main():
    for a, b in ((5, 7), (255, 1), (127, 1)):
        result, flags = add(a, b)
        print(f"{a} + {b} -> bits={result:08b}, unsigned={result}, signed={signed(result)}, {flags}")


if __name__ == "__main__":
    main()
