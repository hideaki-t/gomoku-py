#include <string.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>

//#define USED(bits, pos) ((bits[pos/64] >> (pos % 64)) & 1)
//#define USE(bits, pos) (bits[pos/64] |= (1UL << (pos % 64)))

bool USED(const uint64_t *bits, const int pos) {
    if ((bits[pos/64] >> (pos % 64)) & 1) {
	return true;
    }
    return false;
}
void USE(uint64_t *bits, const int pos) {
    bits[pos/64] |= (1UL << (pos % 64));
}

struct nodealloc {
    int *nexts;
    int *prevs;
    uint64_t *used;
};

static void init_array(int *array, const unsigned int size, const int initial) {
    int value = initial;
    for (unsigned int i = 0; i < size; i++) {
	array[i] = value++;
    }
}

struct nodealloc *getnodealloc(const unsigned int size) {
    struct nodealloc *a = malloc(sizeof(struct nodealloc));
    if (a != NULL) {
	a->nexts = malloc(sizeof(int) * (size * 2));
	a->used = malloc(sizeof(uint64_t) * ((size / 64) + 1));
	if (a->nexts == NULL || a->used == NULL) {
	    if (a->nexts != NULL) free(a->nexts);
	    if (a->used != NULL) free(a->used);
	    free(a);
	    a = NULL;
	} else {
	    a->prevs = a->nexts + size;
	    init_array(a->nexts, size, 1);
	    init_array(a->prevs, size, -1);
	    memset(a->used, 0, (size/64) + 1);
	    USE(a->used, 0);
	}
    }
    return a;
}

static bool canalloc(const struct nodealloc *na, const int base,
		   const unsigned short *codes, const unsigned int codelen) {
    const int *nexts = na->nexts;
    for (unsigned int i = 0; i < codelen; ++i) {
	if (nexts[base + codes[i]] == -1) {
	    return false;
	}
    }
    return true;
}

static void alloc(const struct nodealloc *na, const int base,
		  const unsigned short *codes, const unsigned int codelen) {
    int *nexts = na->nexts;
    int *prevs = na->prevs;
    for (unsigned int i = 0; i < codelen; ++i) {
	unsigned int index = base + codes[i];
	nexts[prevs[index]] = nexts[index];
	prevs[nexts[index]] = prevs[index];
	nexts[index] = prevs[index] = -1;
    }
}

int allocate(const struct nodealloc *na,
	     const unsigned short *codes, const unsigned int codelen) {
    const int first = codes[0];
    int cur = 0;
    while (1) {
	cur = na->nexts[cur];
	int base = cur - first;
	if (base >= 0) {
	    if (!USED(na->used, base) && canalloc(na, base, codes, codelen)) {
		alloc(na, base, codes, codelen);
		USE(na->used, base);
		return base;
	    }
	}
    }
}
