import array


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
            if v not in node.child: return
            node = node.child[v]
        for c in node.child.values():
            yield c.collect_values()


    def bulid(self, keys):
        node = self.root
        for key in keys:
            self.insert(key)

class DoubleArray:
    def __init__(self, f):
        self.base = array.array('I')
        self.chck = array.array('H')
        self.opts = array.array('H')

    def getid(self, key):
        return 0
    # surface
    # nodecount(4byte)
    # node(8byte) * nodecount

    # code-map
    # codelimit(4byte)
    # charcode(2byte) * codelimit
