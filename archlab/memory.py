from archlab.bits import unsigned


class Register:
    def __init__(self, width=8):
        unsigned(0, width)
        self.width = width
        self.value = 0

    def write(self, value):
        self.value = unsigned(value, self.width)


class Memory:
    """Byte-addressed memory with explicit bounds checks."""
    def __init__(self, size=256):
        if size < 1:
            raise ValueError("size must be positive")
        self.data = bytearray(size)

    def check(self, address):
        if not 0 <= address < len(self.data):
            raise ValueError(f"address out of range: {address}")

    def read(self, address):
        self.check(address)
        return self.data[address]

    def write(self, address, value):
        self.check(address)
        self.data[address] = unsigned(value)


def main():
    memory, register = Memory(), Register()
    memory.write(16, 42)
    register.write(memory.read(16))
    memory.write(16, 99)
    print(f"Memory[16]={memory.read(16)}, register={register.value}")
    print("Loading copies a value. Changing memory does not update the register.")


if __name__ == "__main__":
    main()
