import array
import itertools


class NodeAllocator:
    def __init__(self, size):
        self.nexts = array.array('i', range(1, size + 1))
        self.prevs = array.array('i', range(-1, size - 1))
        self.used = array.array('Q', itertools.repeat(0, (size//64) + 1))
        self.size = size

    def isused(self, p):
        return (self.used[p//64] >> (p % 64)) & 1

    def use(self, p):
        self.used[p//64] |= (1 << (p % 64))

    def allocate(self, codes):
        nexts = self.nexts
        isused = self.isused
        first = codes[0]
        cur = 0
        while True:
            cur = nexts[cur]
            base = cur - first
            if base < 0:
                continue
            if not isused(base) and all(nexts[base + c] != -1 for c in codes):
                self.__alloc(base, codes)
                self.use(base)
                return base

    def __alloc(self, base, codes):
        nexts = self.nexts
        prevs = self.prevs
        for c in codes:
            index = base + c
            if nexts[index] == -1 or prevs[index] == -1:
                raise Exception()
            nexts[prevs[index]] = nexts[index]
            prevs[nexts[index]] = prevs[index]
            nexts[index] = prevs[index] = -1
