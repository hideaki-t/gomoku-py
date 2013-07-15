import array
import csv
import collections
import itertools
import queue
import struct
from nodealloc import NodeAllocator
from nodealloc_c import NodeAllocator


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

    def insert(self, text):
        node = self.root
        for v in array.array('H', text.encode('UTF-16-LE')):
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


def calc_nodeopt(node):
    return (1 if node.terminal else 0) + \
        (len(node.sibling.children) if node.sibling else 0)


class CodeCounter:
    def __init__(self):
        self.codemap = array.array('H', itertools.repeat(0, 0x10000))
        self.cur = 0

    def getcode(self, child):
        v = child.value
        cmap = self.codemap
        c = cmap[v]
        if c == 0:
            c = self.cur = self.cur + 1
            print(v, cmap[v], c)
            cmap[v] = c
        return c


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
    print("count trie node")
    limit = trie.getnodecount() * 4
    base = array.array('I', itertools.repeat(0, limit))
    check = array.array('H', itertools.repeat(0xffff, limit))
    opts = array.array('I', itertools.repeat(0, limit))
    allocator = NodeAllocator(limit)
    codecounter = CodeCounter()
    getcode = codecounter.getcode
    children = trie.root.children.values()
    memo = {}
    q = queue.PriorityQueue()
    counter = itertools.count(limit, step=-1)
    # * use counter to prevent comparing Trie.Node(dose not have __lt__)
    # * process the node which has largest number of child nodes.
    #   smaller value means higher priority in PriorityQueue
    # http://docs.python.org/3/library/heapq.html#priority-queue-implementation-notes
    q.put((-len(children), next(counter), children, trie.root, 0))
    while not q.empty():
        _, _, cldrn, node, idx = q.get()
        firstchild = node.children[next(reversed(node.children))] if node.children else None
        print("n{} c{} l{}".format(node.value, firstchild.value if firstchild else -1, len(cldrn)))
        opts[idx] = calc_nodeopt(node)
        baseidx = memo.get(firstchild)
        if baseidx is not None:
            base[idx] = baseidx
        elif cldrn:
            baseidx = allocator.allocate([getcode(c) for c in cldrn])
            memo[firstchild] = baseidx
            for cld in cldrn:
                g_children = cld.children.values()
                arc = getcode(cld)
                nxt = baseidx + arc
                check[nxt] = arc
                q.put((limit - len(g_children), next(counter), g_children, cld, nxt))
