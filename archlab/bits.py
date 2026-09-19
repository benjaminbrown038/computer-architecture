def unsigned(value, width=8):
    """Keep the low width bits of an integer."""
    if width < 1:
        raise ValueError("width must be positive")
    return value & ((1 << width) - 1)


def signed(value, width=8):
    value = unsigned(value, width)
    return value - (1 << width) if value & (1 << (width - 1)) else value


def main():
    for value in (5, 127, 128, 255, 256, -1):
        encoded = unsigned(value)
        print(f"input={value:4} bits={encoded:08b} unsigned={encoded:3} signed={signed(encoded):4}")


if __name__ == "__main__":
    main()
