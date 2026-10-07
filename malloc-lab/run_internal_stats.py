import csv
import re
import shutil
import subprocess
from pathlib import Path

FITS = {
    "first": Path("mm_first_fit_stats.c"),
    "best": Path("mm_best_fit_stats.c"),
    "next": Path("mm_next_fit_stats.c"),
}

TRACES = [
    "amptjp-bal.rep",
    "binary-bal.rep",
    "random-bal.rep",
]

rows = []


def run(cmd):
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )


for fit, source in FITS.items():

    print()
    print("=" * 60)
    print(f"{fit.upper()} FIT")
    print("=" * 60)

    shutil.copyfile(source, "mm.c")

    run(["make", "clean"])
    build = run(["make"])

    if build.returncode != 0:
        print(build.stdout)
        raise SystemExit(f"{fit}: build failed")

    for trace in TRACES:

        result = run([
            "./mdriver",
            "-v",
            "-f",
            f"traces/{trace}"
        ])

        if result.returncode != 0:
            print(result.stdout)
            raise SystemExit(f"{fit}/{trace}: run failed")

        output = result.stdout

        def number(pattern):
            m = re.search(pattern, output)
            return m.group(1) if m else ""

        calls = number(r"find_fit calls\s*:\s*(\d+)")
        checks = number(r"find_fit checks\s*:\s*(\d+)")
        avg = number(r"avg checks per call\s*:\s*([\d.]+)")
        sbrk = number(r"mem_sbrk calls\s*:\s*(\d+)")
        heap = number(r"heap size\s*:\s*(\d+)")

        print(
            f"{trace:20s} "
            f"calls={calls} "
            f"checks={checks} "
            f"avg={avg} "
            f"sbrk={sbrk} "
            f"heap={heap}"
        )

        rows.append({
            "fit": fit,
            "trace": trace,
            "find_fit_calls": calls,
            "find_fit_checks": checks,
            "avg_checks_per_call": avg,
            "mem_sbrk_calls": sbrk,
            "heap_size_bytes": heap,
        })


with open("internal_stats.csv", "w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "fit",
            "trace",
            "find_fit_calls",
            "find_fit_checks",
            "avg_checks_per_call",
            "mem_sbrk_calls",
            "heap_size_bytes",
        ]
    )

    writer.writeheader()
    writer.writerows(rows)

print()
print("완료: internal_stats.csv")
