from pathlib import Path

FILES = {
    "first": Path("mm_first_fit.c"),
    "best": Path("mm_best_fit.c"),
    "next": Path("mm_next_fit.c"),
}

COMMON_DECL = r'''
static size_t find_fit_calls = 0;
static size_t find_fit_checks = 0;
static size_t sbrk_calls = 0;

static int stats_registered = 0;
static void mm_print_stats(void);
'''

PRINT_FUNC = r'''

static void mm_print_stats(void)
{
    printf("\n=== Allocator Stats ===\n");
    printf("find_fit calls      : %zu\n", find_fit_calls);
    printf("find_fit checks     : %zu\n", find_fit_checks);

    if (find_fit_calls > 0)
    {
        printf("avg checks per call : %.2f\n",
               (double)find_fit_checks / find_fit_calls);
    }

    printf("mem_sbrk calls      : %zu\n", sbrk_calls);
    printf("heap size           : %zu bytes\n", mem_heapsize());
}
'''


def must_replace(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"치환 실패: {label}")
    return text.replace(old, new, 1)


for fit, path in FILES.items():
    text = path.read_text()

    # -------------------------------------------------
    # 1. 통계 변수 추가
    # -------------------------------------------------
    text = must_replace(
        text,
        "static char *heap_listp = NULL;",
        "static char *heap_listp = NULL;\n" + COMMON_DECL,
        f"{fit}: declarations"
    )

    # -------------------------------------------------
    # 2. mm_init 시작 시 카운터 초기화 + atexit 등록
    # -------------------------------------------------
    text = must_replace(
        text,
        """int mm_init(void)
{
""",
        """int mm_init(void)
{
    find_fit_calls = 0;
    find_fit_checks = 0;
    sbrk_calls = 0;

    if (!stats_registered)
    {
        atexit(mm_print_stats);
        stats_registered = 1;
    }

""",
        f"{fit}: mm_init"
    )

    # -------------------------------------------------
    # 3. 최초 mem_sbrk 횟수
    # -------------------------------------------------
    text = must_replace(
        text,
        """if ((heap_listp = mem_sbrk(4 * WSIZE)) == (void *)-1)
        return -1;
""",
        """if ((heap_listp = mem_sbrk(4 * WSIZE)) == (void *)-1)
        return -1;

    sbrk_calls++;
""",
        f"{fit}: initial sbrk"
    )

    # -------------------------------------------------
    # 4. extend_heap의 mem_sbrk 횟수
    # -------------------------------------------------
    text = must_replace(
        text,
        """if ((bp = mem_sbrk(size)) == (void *)-1)
        return NULL;
""",
        """if ((bp = mem_sbrk(size)) == (void *)-1)
        return NULL;

    sbrk_calls++;
""",
        f"{fit}: extend sbrk"
    )

    # -------------------------------------------------
    # 5. find_fit 호출 횟수
    # -------------------------------------------------
    marker = "static void *find_fit(size_t asize)\n{"
    text = must_replace(
        text,
        marker,
        marker + "\n    find_fit_calls++;",
        f"{fit}: find_fit calls"
    )

    # -------------------------------------------------
    # 6. 블록 검사 횟수
    # -------------------------------------------------
    if fit in ("first", "best"):
        old = """for (bp = heap_listp;
         GET_SIZE(HDRP(bp)) > 0;
         bp = NEXT_BLKP(bp))
    {
"""
        new = """for (bp = heap_listp;
         GET_SIZE(HDRP(bp)) > 0;
         bp = NEXT_BLKP(bp))
    {
        find_fit_checks++;
"""
        text = must_replace(
            text, old, new,
            f"{fit}: find_fit checks"
        )

    elif fit == "next":
        old1 = """for (;
         GET_SIZE(HDRP(rover)) > 0;
         rover = NEXT_BLKP(rover))
    {
"""
        new1 = """for (;
         GET_SIZE(HDRP(rover)) > 0;
         rover = NEXT_BLKP(rover))
    {
        find_fit_checks++;
"""

        old2 = """for (rover = heap_listp;
         rover < oldrover;
         rover = NEXT_BLKP(rover))
    {
"""
        new2 = """for (rover = heap_listp;
         rover < oldrover;
         rover = NEXT_BLKP(rover))
    {
        find_fit_checks++;
"""

        text = must_replace(
            text, old1, new1,
            "next: first loop"
        )

        text = must_replace(
            text, old2, new2,
            "next: second loop"
        )

    # -------------------------------------------------
    # 7. 출력 함수 추가
    # -------------------------------------------------
    text += PRINT_FUNC

    out = Path(f"mm_{fit}_fit_stats.c")
    out.write_text(text)

    print(f"created: {out}")

print("완료")
