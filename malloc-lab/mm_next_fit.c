/*
 * mm.c - Implicit Free List + Next Fit
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

#include "mm.h"
#include "memlib.h"

team_t team = {
    "ateam",
    "Harry Bovik",
    "bovik@cs.cmu.edu",
    "",
    ""
};

#define ALIGNMENT 8
#define ALIGN(size) (((size) + (ALIGNMENT - 1)) & ~0x7)

#define WSIZE       4
#define DSIZE       8
#define CHUNKSIZE   (1 << 12)

#define MAX(x, y) ((x) > (y) ? (x) : (y))

#define PACK(size, alloc) ((size) | (alloc))

#define GET(p) (*(unsigned int *)(p))
#define PUT(p, val) (*(unsigned int *)(p) = (val))

#define GET_SIZE(p)  (GET(p) & ~0x7)
#define GET_ALLOC(p) (GET(p) & 0x1)

#define HDRP(bp) ((char *)(bp) - WSIZE)
#define FTRP(bp) ((char *)(bp) + GET_SIZE(HDRP(bp)) - DSIZE)

#define NEXT_BLKP(bp) \
    ((char *)(bp) + GET_SIZE(HDRP(bp)))

#define PREV_BLKP(bp) \
    ((char *)(bp) - GET_SIZE(((char *)(bp) - DSIZE)))

static char *heap_listp = NULL;

/*
 * Next Fit에서 마지막 탐색 위치를 기억한다.
 */
static char *rover = NULL;

static void *extend_heap(size_t words);
static void *coalesce(void *bp);
static void *find_fit(size_t asize);
static void place(void *bp, size_t asize);


/*
 * mm_init
 */
int mm_init(void)
{
    if ((heap_listp = mem_sbrk(4 * WSIZE)) == (void *)-1)
        return -1;

    PUT(heap_listp, 0);
    PUT(heap_listp + WSIZE, PACK(DSIZE, 1));
    PUT(heap_listp + 2 * WSIZE, PACK(DSIZE, 1));
    PUT(heap_listp + 3 * WSIZE, PACK(0, 1));

    heap_listp += 2 * WSIZE;

    /*
     * Next Fit의 최초 탐색 위치.
     */
    rover = heap_listp;

    if (extend_heap(CHUNKSIZE / WSIZE) == NULL)
        return -1;

    return 0;
}


/*
 * extend_heap
 */
static void *extend_heap(size_t words)
{
    char *bp;
    size_t size;

    size = (words % 2)
        ? (words + 1) * WSIZE
        : words * WSIZE;

    if ((bp = mem_sbrk(size)) == (void *)-1)
        return NULL;

    PUT(HDRP(bp), PACK(size, 0));
    PUT(FTRP(bp), PACK(size, 0));

    PUT(HDRP(NEXT_BLKP(bp)), PACK(0, 1));

    return coalesce(bp);
}


/*
 * coalesce
 */
static void *coalesce(void *bp)
{
    size_t prev_alloc;
    size_t next_alloc;
    size_t size;

    prev_alloc = GET_ALLOC(FTRP(PREV_BLKP(bp)));
    next_alloc = GET_ALLOC(HDRP(NEXT_BLKP(bp)));
    size = GET_SIZE(HDRP(bp));

    /*
     * Case 1
     */
    if (prev_alloc && next_alloc)
    {
        return bp;
    }

    /*
     * Case 2
     */
    else if (prev_alloc && !next_alloc)
    {
        size += GET_SIZE(HDRP(NEXT_BLKP(bp)));

        PUT(HDRP(bp), PACK(size, 0));
        PUT(FTRP(bp), PACK(size, 0));
    }

    /*
     * Case 3
     */
    else if (!prev_alloc && next_alloc)
    {
        size += GET_SIZE(HDRP(PREV_BLKP(bp)));

        PUT(HDRP(PREV_BLKP(bp)), PACK(size, 0));
        PUT(FTRP(bp), PACK(size, 0));

        bp = PREV_BLKP(bp);
    }

    /*
     * Case 4
     */
    else
    {
        size += GET_SIZE(HDRP(PREV_BLKP(bp)))
              + GET_SIZE(HDRP(NEXT_BLKP(bp)));

        PUT(HDRP(PREV_BLKP(bp)), PACK(size, 0));
        PUT(FTRP(NEXT_BLKP(bp)), PACK(size, 0));

        bp = PREV_BLKP(bp);
    }

    /*
     * coalesce 때문에 rover가 합쳐져 사라진 블록 내부를
     * 가리키게 되는 경우, 새 free block의 시작으로 옮긴다.
     */
    if (rover > (char *)bp &&
        rover < (char *)NEXT_BLKP(bp))
    {
        rover = bp;
    }

    return bp;
}


/*
 * find_fit - Next Fit
 *
 * 지난번 검색 위치부터 heap 끝까지 탐색한다.
 * 없으면 heap 처음으로 돌아가서
 * 원래 검색 위치까지 탐색한다.
 */
static void *find_fit(size_t asize)
{
    char *oldrover;

    oldrover = rover;

    /*
     * 1. 현재 rover부터 heap 끝까지.
     */
    for (;
         GET_SIZE(HDRP(rover)) > 0;
         rover = NEXT_BLKP(rover))
    {
        if (!GET_ALLOC(HDRP(rover)) &&
            GET_SIZE(HDRP(rover)) >= asize)
        {
            return rover;
        }
    }

    /*
     * 2. heap 처음부터 기존 rover 위치까지.
     */
    for (rover = heap_listp;
         rover < oldrover;
         rover = NEXT_BLKP(rover))
    {
        if (!GET_ALLOC(HDRP(rover)) &&
            GET_SIZE(HDRP(rover)) >= asize)
        {
            return rover;
        }
    }

    return NULL;
}


/*
 * place
 */
static void place(void *bp, size_t asize)
{
    size_t csize;

    csize = GET_SIZE(HDRP(bp));

    if ((csize - asize) >= (2 * DSIZE))
    {
        PUT(HDRP(bp), PACK(asize, 1));
        PUT(FTRP(bp), PACK(asize, 1));

        bp = NEXT_BLKP(bp);

        PUT(HDRP(bp), PACK(csize - asize, 0));
        PUT(FTRP(bp), PACK(csize - asize, 0));
    }
    else
    {
        PUT(HDRP(bp), PACK(csize, 1));
        PUT(FTRP(bp), PACK(csize, 1));
    }
}


/*
 * mm_malloc
 */
void *mm_malloc(size_t size)
{
    size_t asize;
    size_t extendsize;
    char *bp;

    if (size == 0)
        return NULL;

    asize = MAX(ALIGN(size + DSIZE), 2 * DSIZE);

    if ((bp = find_fit(asize)) != NULL)
    {
        place(bp, asize);
        return bp;
    }

    extendsize = MAX(asize, CHUNKSIZE);

    if ((bp = extend_heap(extendsize / WSIZE)) == NULL)
        return NULL;

    place(bp, asize);

    return bp;
}


/*
 * mm_free
 */
void mm_free(void *bp)
{
    size_t size;

    if (bp == NULL)
        return;

    size = GET_SIZE(HDRP(bp));

    PUT(HDRP(bp), PACK(size, 0));
    PUT(FTRP(bp), PACK(size, 0));

    coalesce(bp);
}


/*
 * mm_realloc
 */
void *mm_realloc(void *ptr, size_t size)
{
    void *newptr;
    size_t copySize;

    if (ptr == NULL)
        return mm_malloc(size);

    if (size == 0)
    {
        mm_free(ptr);
        return NULL;
    }

    newptr = mm_malloc(size);

    if (newptr == NULL)
        return NULL;

    copySize = GET_SIZE(HDRP(ptr)) - DSIZE;

    if (size < copySize)
        copySize = size;

    memcpy(newptr, ptr, copySize);

    mm_free(ptr);

    return newptr;
}
