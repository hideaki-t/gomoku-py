import os.path
import struct
import collections
import re
import itertools


def main(indir, outdir, enc='euc-jp'):
    # check output directry in main
    build_matrix(open(os.path.join(indir, 'matrix.def'), encoding=enc),
                 open(os.path.join(outdir, 'matrix.bin'), 'wb'))
    build_pos(open(os.path.join(indir, 'left-id.def'), encoding=enc),
              open(os.path.join(outdir, 'pos.bin'), 'w', encoding='utf-8'))
    build_char_category(open(os.path.join(indir, 'char.def'), encoding=enc),
                        open(os.path.join(outdir, 'category.bin'), 'wb'))
    build_code_category(open(os.path.join(indir, 'char.def'), encoding=enc),
                        open(os.path.join(outdir, 'code.bin'), 'wb'))


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

comment = re.compile('#.*$')


def parse_char_category(i):
    for l in i:
        l = comment.sub('', l.strip())
        if len(l) == 0 or l.startswith('0x'):
            continue
        yield l.split()[:4]


def build_char_category(i, o):
    categories = collections.OrderedDict()
    for name, invoke, group, length in parse_char_category(i):
        categories[name] = [int(x) for x in (invoke, group, length)]
    o.write(struct.pack('!I', len(categories)))
    for v in categories.values():
        o.write(struct.pack('BBB', v[0], v[1], v[2]))


def build_code_category(i, o):
    def parse(i):
        for l in i:
            l = comment.sub('', l.strip())
            if l.startswith('0x'):
                rng, *names = l.split()
                # range: 0xXXXX or 0xXXXX..0xXXXX
                begin = int(rng[:6], 16)
                end = begin if len(rng) == 6 else int(rng[8:], 16)
                yield names, begin, end

    i1, i2 = itertools.tee(i)
    categories = [n[0] for n in parse_char_category(i1)]
    default_cid = categories.index('DEFAULT')
    codes = [[default_cid, 1 << default_cid] for x in range(0x10000)]
    for names, begin, end in parse(i2):
        cid = categories.index(names[0])
        mask = 0
        for name in names:
            mask |= 1 << (categories.index(name))
        for c in range(begin, end+1):
            codes[c] = [cid, mask]
    o.write(struct.pack('!I', len(codes)))
    for cid, mask in codes:
        o.write(struct.pack('B', cid))
        o.write(struct.pack('!H', mask))
