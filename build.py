import os.path
import struct
import collections
import re
import itertools
import csv
from doublearray import DoubleArray


def main(indir, outdir, enc='euc-jp'):
    # check output directry in main
    print('matrix')
    build_matrix(open(os.path.join(indir, 'matrix.def'), encoding=enc),
                 open(os.path.join(outdir, 'matrix.bin'), 'wb'))
    print('pos')
    build_pos(open(os.path.join(indir, 'left-id.def'), encoding=enc),
              open(os.path.join(outdir, 'pos.bin'), 'w', encoding='utf-8'))
    print('char')
    build_char_category(open(os.path.join(indir, 'char.def'), encoding=enc),
                        open(os.path.join(outdir, 'category.bin'), 'wb'))
    print('code')
    build_code_category(open(os.path.join(indir, 'char.def'), encoding=enc),
                        open(os.path.join(outdir, 'code.bin'), 'wb'))
    print('da')
    build_doublearray(outdir)
    print('morp')
    da = DoubleArray('')
    build_morp(os.path.join(indir, 'char.def'),
               os.path.join(indir, 'unk.def'),
               [x for x in [os.path.join(indir, x) for x in os.listdir(indir)
                if x.endswith('.csv')] if os.path.isfile(x)],
               da,
               os.path.join(outdir, 'morp.bin'),
               os.path.join(outdir, 'id-morphemes-map.bin'),
               enc)


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


def get_category_names(i):
    return [n[0] for n in parse_char_category(i)]


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
    categories = get_category_names(i1)
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


def build_doublearray(outdir):
    pass


def collect_morphs(chardef, unkdef, csvs, da, encoding):
    def parse(csvs, encoding):
        for row in itertools.chain.from_iterable(
                csv.reader(open(f, encoding=encoding)) for f in csvs):
            if len(row):
                # [0:surface], [1:left-pos], 2:right-pos, [3:cost], 4:feature
                yield row[0], int(row[1]), int(row[3])

    categories = get_category_names(open(chardef, encoding=encoding))
    offset = len(categories)
    morps = collections.defaultdict(list)
    for surface, posid, cost in parse([unkdef], encoding=encoding):
        morpid = categories.index(surface)
        morps[morpid].append((posid, cost))

    for surface, posid, cost in parse(csvs, encoding=encoding):
        morpid = da.getid(surface)
        morps[offset + morpid].append((posid, cost))
    return morps


def morpdict_tolist(morps):
    def lowcost_cut_filter(idcost_pair):
        # order by pos-id and keep the highest cost
        return [next(v) for k, v in itertools.groupby(
            sorted(idcost_pair, reverse=True), key=lambda x: x[0])]

    morplist = [None] * len(morps)
    for morpid, vs in morps.items():
        morplist[morpid] = lowcost_cut_filter(vs)
    return morplist


def build_morp(chardef, unkdef, csvs, da, morpbin, idmorpmap, encoding):
    morplist = morpdict_tolist(
        collect_morphs(chardef, unkdef, csvs, da, encoding))

    with open(morpbin, 'wb') as o:
        o.write(struct.pack("!I", sum(len(vs) for vs in morplist)))
        for vs in morplist:
            for posid, cost in vs:
                o.write(struct.pack("!H", posid))
                o.write(struct.pack("!H", cost))

    with open(idmorpmap, 'wb') as o:
        o.write(struct.pack("!I", len(morplist)))
        for vs in morplist:
            o.write(struct.pack('B', len(vs)))
