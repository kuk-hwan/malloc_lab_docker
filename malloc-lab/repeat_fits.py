import csv
import re
import shutil
import statistics
import subprocess
from pathlib import Path

ROOT = Path(".")
REPEAT = 10

FITS = {
    "first": ROOT / "mm_first_fit.c",
    "best": ROOT / "mm_best_fit.c",
    "next": ROOT / "mm_next_fit.c",
}

TRACES = sorted((ROOT / "traces").glob("*-bal.rep"))

RAW_OUTPUT = ROOT / "fit_repeat_results.csv"
SUMMARY_OUTPUT = ROOT / "fit_repeat_summary.csv"


def run(cmd):
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )


def parse_output(output):
    valid = ""
    util = None
    ops = None
    secs = None
    kops = None
    perf = None

    # valid
    m = re.search(
        r"^\s*0\s+(yes|no)\s+",
        output,
        re.MULTILINE
    )
    if m:
        valid = m.group(1)

    # Total line
    # 예:
    # Total          92%    4800  0.005127   936
    #
    # 붙는 경우도 처리:
    # Total          66%   14400  0.000066218845
    m = re.search(
        r"^Total\s+"
        r"(\d+)%\s+"
        r"(\d+)\s+"
        r"(\d+\.\d{6})"
        r"\s*(\d+)?\s*$",
        output,
        re.MULTILINE
    )

    if m:
        util = int(m.group(1))
        ops = int(m.group(2))
        secs = float(m.group(3))

        if m.group(4):
            kops = int(m.group(4))

    # Perf
    m = re.search(
        r"Perf index\s*=\s*"
        r"\d+\s*\(util\)\s*\+\s*"
        r"\d+\s*\(thru\)\s*=\s*"
        r"(\d+)/100",
        output
    )

    if m:
        perf = int(m.group(1))

    return valid, util, ops, secs, kops, perf


all_rows = []

for fit_name, source in FITS.items():

    print()
    print("=" * 60)
    print(f"{fit_name.upper()} FIT")
    print("=" * 60)

    shutil.copyfile(source, ROOT / "mm.c")

    run(["make", "clean"])
    build = run(["make"])

    if build.returncode != 0:
        print(f"[BUILD ERROR] {fit_name}")
        print(build.stdout)
        continue

    for trace in TRACES:

        print()
        print(f"[{fit_name}] {trace.name}")

        for i in range(1, REPEAT + 1):

            result = run([
                "./mdriver",
                "-v",
                "-f",
                str(trace)
            ])

            if result.returncode != 0:
                print(f"  run {i:2d}: RUN ERROR")

                all_rows.append({
                    "fit": fit_name,
                    "trace": trace.name,
                    "run": i,
                    "status": "RUN_ERROR",
                    "valid": "",
                    "util": "",
                    "ops": "",
                    "secs": "",
                    "kops": "",
                    "perf": "",
                })

                continue

            valid, util, ops, secs, kops, perf = \
                parse_output(result.stdout)

            status = "OK"

            if valid == "" or util is None or perf is None:
                status = "PARSE_ERROR"

            print(
                f"  run {i:2d}: "
                f"util={util} "
                f"kops={kops} "
                f"perf={perf}"
            )

            all_rows.append({
                "fit": fit_name,
                "trace": trace.name,
                "run": i,
                "status": status,
                "valid": valid,
                "util": util,
                "ops": ops,
                "secs": secs,
                "kops": kops,
                "perf": perf,
            })


# -------------------------
# Raw CSV
# -------------------------

with RAW_OUTPUT.open("w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "fit",
            "trace",
            "run",
            "status",
            "valid",
            "util",
            "ops",
            "secs",
            "kops",
            "perf",
        ]
    )

    writer.writeheader()
    writer.writerows(all_rows)


# -------------------------
# Summary CSV
# -------------------------

summary_rows = []

for fit_name in FITS:

    for trace in TRACES:

        rows = [
            r for r in all_rows
            if r["fit"] == fit_name
            and r["trace"] == trace.name
            and r["status"] == "OK"
            and r["kops"] not in ("", None)
        ]

        if not rows:
            continue

        kops_values = [int(r["kops"]) for r in rows]
        secs_values = [float(r["secs"]) for r in rows]
        util_values = [int(r["util"]) for r in rows]
        perf_values = [int(r["perf"]) for r in rows]

        summary_rows.append({
            "fit": fit_name,
            "trace": trace.name,
            "runs": len(rows),

            "util": statistics.median(util_values),

            "mean_secs": round(
                statistics.mean(secs_values), 6
            ),

            "mean_kops": round(
                statistics.mean(kops_values), 2
            ),

            "median_kops": round(
                statistics.median(kops_values), 2
            ),

            "min_kops": min(kops_values),

            "max_kops": max(kops_values),

            "stdev_kops": round(
                statistics.stdev(kops_values), 2
                if len(kops_values) > 1 else 0
            ),

            "mean_perf": round(
                statistics.mean(perf_values), 2
            ),
        })


with SUMMARY_OUTPUT.open("w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "fit",
            "trace",
            "runs",
            "util",
            "mean_secs",
            "mean_kops",
            "median_kops",
            "min_kops",
            "max_kops",
            "stdev_kops",
            "mean_perf",
        ]
    )

    writer.writeheader()
    writer.writerows(summary_rows)


print()
print("=" * 60)
print("완료")
print(f"개별 결과 : {RAW_OUTPUT}")
print(f"요약 결과 : {SUMMARY_OUTPUT}")
print("=" * 60)
