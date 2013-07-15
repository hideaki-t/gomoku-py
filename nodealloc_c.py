import time
from ctypes import *


class NA(Structure):
    __fields__ = [("nexts", POINTER(c_int)),
                  ("prevs", POINTER(c_int)),
                  ("used", POINTER(c_longlong))]


nadll = cdll.LoadLibrary('./_nodealloc_c.so')
getnodealloc = CFUNCTYPE(POINTER(NA), c_uint)(("getnodealloc", nadll))
allocate = CFUNCTYPE(c_int, POINTER(NA), POINTER(c_ushort), c_uint)(("allocate", nadll))

class NodeAllocator:
    def __init__(self, size):
        self.na = getnodealloc(size).contents
        self.size = size

    def allocate(self, codes):
        start = time.clock()
        cds = (c_ushort * len(codes))(*codes)
        base = allocate(self.na, cds, len(codes))
        print('allocated', base, time.clock() - start)
        return base
