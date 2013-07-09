import os.path
import struct


def main(indir, outdir, encoding='euc-jp'):
    # check output directry in main
    build_matrix(open(os.path.join(indir, 'matrix.def'), encoding=encoding),
                 open(os.path.join(outdir, 'matrix.bin'), 'wb'))
    build_pos(open(os.path.join(indir, 'left-id.def'), encoding=encoding),
              open(os.path.join(outdir, 'pos.bin'), 'w', encoding='utf-8'))

def build_matrix(i, o):
    ''' build matrix.bin from matrix.def '''
    leftnum, rightnum = map(int, i.readline().split(' '))
    o.write(struct.pack('!II', leftnum, rightnum))
    for l in range(leftnum):
        for r in range(rightnum):
            lv, rv, cost = map(int, i.readline().split(' '))
            assert lv == l and rv == r
            o.write(struct.pack('!h', int(cost)))

def build_pos(i, o):
    for l in i:
        pos = l.split(' ')[1]
        o.write(pos[:pos.rindex(',')])
        o.write('\n')
