"""Direct-mapped, read-only cache tag model; no data or real timing."""


class Cache:
    def __init__(self, lines=4, block_size=4):
        if lines < 1 or block_size < 1:
            raise ValueError("cache dimensions must be positive")
        self.tags = [None] * lines
        self.block_size = block_size
        self.hits = self.misses = 0

    def read(self, address):
        if address < 0:
            raise ValueError("address must be nonnegative")
        block = address // self.block_size
        index = block % len(self.tags)
        tag = block // len(self.tags)
        hit = self.tags[index] == tag
        self.hits += int(hit)
        self.misses += int(not hit)
        self.tags[index] = tag
        return hit


def main():
    patterns = {"sequential": list(range(32)),
                "reuse": list(range(8)) * 4,
                "conflict": [0, 16] * 16}
    for name, addresses in patterns.items():
        cache = Cache()
        for address in addresses:
            cache.read(address)
        # Assumption: each lookup costs 1 cycle; a miss adds 20 cycles.
        cycles = len(addresses) + cache.misses * 20
        print(f"{name:10} hits={cache.hits:2} misses={cache.misses:2} modeled_cycles={cycles}")


if __name__ == "__main__":
    main()
