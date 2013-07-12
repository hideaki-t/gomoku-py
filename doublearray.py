import array
import csv
import collections
import itertools
import queue
import struct


class Trie:
    class Node:
        def __init__(self, value=None):
            self.value = value
            self.children = collections.OrderedDict()
            self.terminal = False
            self.sibling = None

        def add(self, value):
            child = Trie.Node(value)
            child.sibling = self
            self.children[value] = child

        def collect_values(self):
            if self.terminal:
                yield self.value
            for c in self.children.values():
                for x in c.collect_values():
                    yield self.value + x

    def __init__(self):
        self.root = Trie.Node()

    def insert(self, seq):
        node = self.root
        for v in seq:
            if v not in node.children:
                node.add(v)
            node = node.children[v]
        node.terminal = True

    def common_prefix_search(self, prefix):
        node = self.root
        for v in prefix:
            if v not in node.children:
                return
            node = node.children[v]
        for c in node.children.values():
            yield c.collect_values()

    def bulid(self, keys):
        for key in keys:
            self.insert(key)

    def getnodecount(self):
        def f(node):
            yield node
            for cn in node.children.values():
                for c in f(cn):
                    yield c
        return sum(1 for _ in f(self.root))


def isterminal(node):
    # check 40th bit
    return node & 0x10000000000 != 0


def base(node):
    # 0-23bit(24bit)
    return node & 0xffffff


def chck(node):
    # 24-40bit(16bit)
    return (node >> 24) & 0xffff


def siblings(node):
    # 41-64bit(23bit)
    return (node >> 41) & 0x7fffff


def incid(nid, node):
    return nid + siblings(node) + (1 if isterminal(node) else 0)


class DoubleArray:
    def __init__(self, surfaceid, codemap):
        #self.base = array.array('I')
        #self.chck = array.array('H')
        #self.opts = array.array('H')
        cnt = struct.unpack('!I', surfaceid.read(4))[0]
        self.nodes = array.array('Q')
        self.nodes.fromfile(surfaceid, cnt)
        self.nodes.byteswap()
        codelimit = struct.unpack('!I', codemap.read(4))[0]
        self.codemap = array.array('H')
        self.codemap.fromfile(codemap, codelimit)
        self.codemap.byteswap()

    def getid(self, key):
        nodes = self.nodes
        codemap = self.codemap
        node = 0
        nid = -1
        for c in array.array('H', key.encode('UTF-16-LE')):
            n = nodes[node]
            arc = codemap[c]
            nxt = base(n) + arc
            if chck(nodes[nxt]) != arc:
                return None
            node = nxt
            nid = incid(nid, n)
        if isterminal(nodes[node]):
            return incid(nid, nodes[node])

    # surface
    # nodecount(4byte)
    # node(8byte) * nodecount

    # code-map
    # codelimit(4byte)
    # charcode(2byte) * codelimit

class NodeAllocator:
    def __init__(self, size):
        self.nexts = array.array('i', range(1, size + 1))
        self.prevs = array.array('i', range(-1, size - 1))
        self.used = 1
        self.size = size

    def allocate(self, codes):
        nexts = self.nexts
        used = self.used
        canalloc = self.__canalloc
        alloc = self.__alloc
        first = codes[0]
        cur = 0
        while True:
            cur = nexts[cur]
            base = cur - first
            if base < 0:
                continue
            bit = (1 << base)
            if used & bit == 0 and canalloc(base, codes):
                used |= bit
                for c in codes:
                    alloc(base + c)
                return base

    def __alloc(self, index):
        nexts = self.nexts
        prevs = self.prevs
        if nexts[index] == -1 or prevs[index] == -1:
            raise Exception()
        nexts[prevs[index]] = nexts[index]
        prevs[nexts[index]] = prevs[index]
        nexts[index] = prevs[index] = -1

    def __canalloc(self, base, codes):
        nexts = self.nexts
        return all(nexts[base + c] != -1 for c in codes)


import heapq
class PriorityQueue:
    def __init__(self):
        self.heap = []
    def push(self, value):
        heapq.push()

def calc_nodeopt(node):
    return (1 if node.terminal else 0) + \
        (len(node.sibling.children) if node.sibling else 0)


def build_doublearray(csvs, encoding):
    trie = Trie()
    print("make keys")
    keys = sorted({row[0] for row in itertools.chain.from_iterable(
        csv.reader(open(f, encoding=encoding)) for f in csvs) if row})
    print("insert to trie")
    for k in keys:
        trie.insert(k)
#    for k in sorted({row[0] for row in itertools.chain.from_iterable(
#            csv.reader(open(f, encoding=encoding)) for f in csvs) if row}):
#        trie.insert(k)
    print("alloc codemap")
    codemap = array.array('H', itertools.repeat(0, 0x10000))
    print("count trie node")
    limit = trie.getnodecount()
    print("alloc da")
    da = (array.array('I', itertools.repeat(0, limit)), # base
          array.array('H', itertools.repeat(0xffff, limit)), # check
          array.array('I', itertools.repeat(0, limit))) # opts
    base = 0
    check = 1
    opts = 2
    print("alloc allocator")
    allocator = NodeAllocator(limit)

    cur = 0
    def getcode(child):
        nonlocal cur
        # todo child.value -> code
        v = struct.unpack('!H', child.value.encode('UTF-16-BE'))[0]
        if codemap[v] == 0:
            cur += 1
            print(v, codemap[v], cur)
            codemap[v] = cur
        return codemap[v]

    memo = {}
    children = trie.root.children.values()
    q = queue.PriorityQueue()
    # * use counter to prevent comparing Trie.Node(dose not have __lt__)
    # * process the node which has largest number of child nodes.
    #   smaller value means higher priority in PriorityQueue
    # http://docs.python.org/3/library/heapq.html#priority-queue-implementation-notes
    counter = itertools.count(limit, -1)
    q.put((limit - len(children), next(counter), children, trie.root, 0))
    while not q.empty():
        _, _, cldrn, node, idx = q.get()
        firstchild = next(iter(node.children.values())) if node.children else None
        _1 = ord(node.value) if node.value else -1
        _2 = ord(firstchild.value) if firstchild else -1
        print("n{} c{} l{}".format(_1, _2, len(cldrn)))
        if firstchild in memo:
            da[opts][idx] = calc_nodeopt(node)
            da[base][idx] = 0 ## TODO
            continue

        da[opts][idx] = calc_nodeopt(node)
        if cldrn:
            baseidx = allocator.allocate([getcode(c) for c in cldrn])
            memo[firstchild] = baseidx
            for cld in cldrn:
                g_children = cld.children.values()
                #print(cld.value, len(g_children), next(iter(g_children)).value if g_children else None)
                arc = getcode(cld)
                nxt = baseidx + arc
                da[check][nxt] = arc
                q.put((limit - len(g_children), next(counter), g_children, cld, nxt))
