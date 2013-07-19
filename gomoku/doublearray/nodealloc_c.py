from ctypes import (cdll, c_ushort, c_int, c_uint, c_ulonglong,
                    CFUNCTYPE, POINTER, Structure)


class NodeAllocator:
    class NA(Structure):
        __fields__ = [("nexts", POINTER(c_int)),
                      ("prevs", POINTER(c_int)),
                      ("used", POINTER(c_ulonglong))]

    __nadll = cdll.LoadLibrary('./_nodealloc_c.so')
    __allocate = CFUNCTYPE(c_int, POINTER(NA),
                           POINTER(c_ushort), c_uint)(("allocate", __nadll))

    def __init__(self, size):
        getnodealloc = CFUNCTYPE(POINTER(NodeAllocator.NA),
                                 c_uint)(("getnodealloc", self.__nadll))
        self.na = getnodealloc(size).contents
        self.size = size

    def allocate(self, codes):
        cds = (c_ushort * len(codes))(*codes)
        base = self.__allocate(self.na, cds, len(codes))
        return base
