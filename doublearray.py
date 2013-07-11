import array
import struct


class Trie:
    class Node:
        def __init__(self, value=None):
            self.value = value
            self.child = {}
            self.terminal = False

        def add(self, value):
            self.child[value] = Trie.Node(value)

        def collect_values(self):
            if self.terminal:
                yield self.value
            for c in self.child.values():
                for x in c.collect_values():
                    yield self.value + x

    def __init__(self):
        self.root = Trie.Node()

    def insert(self, seq):
        node = self.root
        for v in seq:
            if v not in node.child:
                node.add(v)
            node = node.child[v]
        node.terminal = True

    def common_prefix_search(self, prefix):
        node = self.root
        for v in prefix:
            if v not in node.child:
                return
            node = node.child[v]
        for c in node.child.values():
            yield c.collect_values()

    def bulid(self, keys):
        for key in keys:
            self.insert(key)


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
