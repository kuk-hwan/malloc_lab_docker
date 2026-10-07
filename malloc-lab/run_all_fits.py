import csv
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(".")
TRACES = sorted((ROOT / "traces").glob("*-bal.rep"))

FITS = {
    "first": ROOT / "mm_first_fit.c",
    "best": ROOT / "mm_best_fit.c",
    "next": ROOT / "mm_next_fit.c",
}

OUTPUT = ROOT / "fit_results.csv"


def run_command(cmd):
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )


def parse_result(output):
    valid = ""
    util = ""
    ops = ""
    secs = ""
    kops = ""
    perf = ""

    # valid
    m = re.search(
        r"^\s*0\s+(yes|no)\s+",
        output,
        re.MULTILINE
    )
    if m:
        valid = m.group(1)

    # Total line
    #
    # 정상:
    # Total          92%    4800  0.005281   909
    #
    # 붙는 경우:
    # Total          94%   14400  0.000104138329
    #
    # secs는 항상 소수점 아래 6자리이므로
    # 0.000104 / 138329 로 분리 가능.
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
        util = m.group(1)
        ops = m.group(2)
        secs = m.group(3)
        kops = m.group(4) or ""

    # Perf index
    m = re.search(
        r"Perf index\s*=\s*"
        r"\d+\s*\(util\)\s*\+\s*"
        r"\d+\s*\(thru\)\s*=\s*"
        r"(\d+)/100",
        output
    )

    if m:
        perf = m.group(1)

    return valid, util, ops, secs, kops, perf


with OUTPUT.open("w", newline="") as f:
    writer = csv.writer(f)

    writer.writerow([
        "fit",
        "trace",
        "status",
        "valid",
        "util",
        "ops",
        "secs",
        "kops",
        "perf"
    ])

    for fit_name, source in FITS.items():

        print()
        print("=" * 60)
        print(f"Testing {fit_name.upper()} FIT")
        print("=" * 60)

        if not source.exists():
            print(f"[ERROR] {source} not found")
            continue

        shutil.copyfile(source, ROOT / "mm.c")

        # Build
        run_command(["make", "clean"])
        build = run_command(["make"])

        if build.returncode != 0:
            print(f"[BUILD ERROR] {fit_name}")
            print(build.stdout)

            for trace in TRACES:
                writer.writerow([
                    fit_name,
                    trace.name,
                    "BUILD_ERROR",
                    "", "", "", "", "", ""
                ])

            continue

        # Traces
        for trace in TRACES:
            print(f"Running {fit_name:5s} : {trace.name}")

            result = run_command([
                "./mdriver",
                "-v",
                "-f",
                str(trace)
            ])

            if result.returncode != 0:
                print(f"  -> RUN_ERROR ({result.returncode})")

                writer.writerow([
                    fit_name,
                    trace.name,
                    "RUN_ERROR",
                    "", "", "", "", "", ""
                ])

                continue

            valid, util, ops, secs, kops, perf = \
                parse_result(result.stdout)

            if not valid or not util or not perf:
                status = "PARSE_ERROR"
                print("  -> PARSE_ERROR")
                print(result.stdout)
            else:
                status = "OK"
                print(
                    f"  -> util={util}% "
                    f"kops={kops} "
                    f"perf={perf}"
                )

            writer.writerow([
                fit_name,
                trace.name,
                status,
                valid,
                util,
                ops,
                secs,
                kops,
                perf
            ])

print()
print("=" * 60)
print(f"Finished: {OUTPUT}")
print("=" * 60)
