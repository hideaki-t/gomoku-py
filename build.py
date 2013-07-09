import os.path
import struct
import collections


def main(indir, outdir, encoding='euc-jp'):
    # check output directry in main
    build_matrix(open(os.path.join(indir, 'matrix.def'), encoding=encoding),
                 open(os.path.join(outdir, 'matrix.bin'), 'wb'))
    build_pos(open(os.path.join(indir, 'left-id.def'), encoding=encoding),
              open(os.path.join(outdir, 'pos.bin'), 'w', encoding='utf-8'))
    build_char_category(open(os.path.join(indir, 'char.def'), encoding=encoding),
              open(os.path.join(outdir, 'category.bin'), 'wb'))

def build_matrix(i, o):
    ''' build matrix.bin from matrix.def '''
    leftnum, rightnum = [int(x) for x in i.readline().split(' ')]
    o.write(struct.pack('!II', leftnum, rightnum))
    for l in range(leftnum):
        for r in range(rightnum):
            lv, rv, cost = [int(x) for x in i.readline().split(' ')]
            assert lv == l and rv == r
            o.write(struct.pack('!h', int(cost)))

def build_pos(i, o):
    for l in i:
        pos = l.split(' ')[1]
        o.write(pos[:pos.rindex(',')])
        o.write('\n')

def build_char_category(i, o):
    def parse(i):
        for l in i:
            if l.startswith('#') or l.strip() == '' or l.startswith('0x'):
                continue
            yield l.split()[:4]

    categories = collections.OrderedDict()
    for name, invoke, group, length in parse(i):
        categories[name] = [int(x) for x in (invoke, group, length)]
    o.write(struct.pack('!I', len(categories)))
    for v in categories.values():
        o.write(struct.pack('BBB', v[0], v[1], v[2]))
