import array
import csv
import itertools
import queue
import struct
try:
    from nodealloc_c import NodeAllocator
except:
    from nodealloc import NodeAllocator


class Trie:
    class Node:
        def __init__(self, value=None):
            self.value = value
            self.child = None
            self.sibling = None
            self.terminal = False

        def add(self, value):
            child = Trie.Node(value)
            child.sibling = self.child
            self.child = child

        def collect_values(self):
            if self.terminal:
                yield self.value
            child = self.child
            while child:
                for childv in child.collect_values():
                    yield self.value + childv
                child = child.sibling

        def get_child(self, c):
            for child in self.collect_children():
                if child.value == c:
                    return child

        def collect_children(self):
            child = self.child
            while child:
                yield child
                child = child.sibling

        def __eq__(self, other):
            return self.child is other.child and \
                self.sibling is other.sibling and \
                self.value == other.value and \
                self.terminal == other.terminal

        def __hash__(self):
            return hash(id(self.child)) + hash(id(self.sibling)) +\
                hash(self.value) + hash(self.terminal)

    def __init__(self):
        self.memo = {}
        self.root = self.share(Trie.Node())

    def share(self, node):
        if not node:
            return None
        n = self.memo.get(node)
        if n:
            return n
        node.chlid = self.share(node.child)
        node.sibling = self.share(node.sibling)
        self.memo[node] = node
        return node

    def insert(self, text):
        node = self.root
        for v in array.array('H', text.encode('UTF-16-LE')):
            if not node.get_child(v):
                node.child = self.share(node.child)
                node.add(v)
            node = node.get_child(v)
        node.terminal = True

    def common_prefix_search(self, prefix):
        node = self.root
        for v in prefix:
            node = node.get_child(v)
            if not node:
                return
        for child in node.collect_children():
            yield child.collect_values()

    def build(self, keys):
        for key in keys:
            self.insert(key)

    def getnodecount(self):
        def f(node):
            yield node
            child = node.child
            while child:
                for g_child in f(child):
                    yield g_child
                child = child.sibling

        return len(set(f(self.root)))


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


def calc_nodeopt(node):
    def f(node):
        v = 0
        q = [node]
        while q:
            n = q.pop()
            if n.terminal:
                v += 1
            if n.sibling:
                q.append(n.sibling)
            if n.child:
                q.append(n.child)
        return v

    if node.sibling is None:
        v = 0
    else:
        v = f(node.sibling) << 1
    return (1 if node.terminal else 0) + v


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
            cmap[v] = c
        return c


def make_keys(csvs, encoding):
    return sorted({row[0] for row in itertools.chain.from_iterable(
        csv.reader(open(f, encoding=encoding)) for f in csvs) if row})


def allocate_arrays(limit):
    return (array.array('I', itertools.repeat(0, limit)),
            array.array('H', itertools.repeat(0xffff, limit)),
            array.array('I', itertools.repeat(0, limit)))


def adjust(base, check, opts):
    maxbase = max(base)
    maxcode = max(x for x in check if x != 0xffff)
    limit = maxbase + maxcode + 1
    return (base[:limit], check[:limit], opts[:limit])


def build_doublearray(csvs, encoding):
    print("build trie")
    trie = Trie()
    trie.build(make_keys(csvs, encoding))
    print("count trie node")
    limit = trie.getnodecount() * 4
    print(limit)
    base, check, opts = allocate_arrays(limit)
    allocator = NodeAllocator(limit)
    codecounter = CodeCounter()
    getcode = codecounter.getcode
    memo = {}
    q = queue.PriorityQueue()
    counter = itertools.count()
    children = list(trie.root.collect_children())[::-1]
    # * use counter to prevent comparing Trie.Node(dose not have __lt__)
    # * process the node which has largest number of child nodes.
    #   smaller value means higher priority in PriorityQueue
    # http://docs.python.org/3/library/heapq.html#priority-queue-implementation-notes
    q.put((-len(children), next(counter),
           children, trie.root, 0))
    while not q.empty():
        _, _, cldrn, node, idx = q.get()
        opts[idx] = calc_nodeopt(node)
        baseidx = memo.get(node.child)
        if baseidx is not None:
            base[idx] = baseidx
        elif cldrn:
            baseidx = allocator.allocate([getcode(c) for c in cldrn])
            memo[node.child] = baseidx
            base[idx] = baseidx
            for cld in cldrn:
                g_children = list(cld.collect_children())[::-1]
                arc = getcode(cld)
                nxt = baseidx + arc
                check[nxt] = arc
                q.put((-len(g_children), next(counter),
                       g_children, cld, nxt))
    import pickle
    pickle.dump((base, check, opts, codecounter.codemap), open('/home/hideaki/da.dump', 'wb'))
    print('build done')
    base, check, opts = adjust(base, check, opts)
    print('adjust done')
    with open('/tmp/surface-id.bin', 'wb') as o:
        o.write(struct.pack('!I', len(base)))
        for i in range(len(base)):
            v = base[i] | (check[i] << 24) | (opts[i] << 40)
            o.write(struct.pack('!Q', v))
    with open('/tmp/code-map.bin', 'wb') as o:
        codemap = codecounter.codemap
        o.write(struct.pack('!I', len(codemap)))
        for c in codemap:
            o.write(struct.pack('!H', c))
    return (base, check, opts, codecounter.codemap)
