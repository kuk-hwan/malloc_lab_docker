#!/bin/bash

OUTPUT="fit_results.csv"

echo "fit,trace,valid,util,ops,secs,kops,perf" > "$OUTPUT"

for FIT in first best next
do
    echo ""
    echo "========================================"
    echo "Testing $FIT fit"
    echo "========================================"

    # 해당 버전을 mm.c로 복사
    cp "mm_${FIT}_fit.c" mm.c

    # 다시 컴파일
    make clean > /dev/null
    make > /dev/null

    # 모든 balanced trace 실행
    for TRACE in traces/*-bal.rep
    do
        TRACE_NAME=$(basename "$TRACE")

        echo "Running $FIT : $TRACE_NAME"

        RESULT=$(./mdriver -v -f "$TRACE" 2>&1)

        # valid 추출
        VALID=$(echo "$RESULT" |
            awk '/^[[:space:]]*0[[:space:]]+/ {print $2; exit}')

        # Total 줄에서 util, ops, secs, Kops 추출
        TOTAL=$(echo "$RESULT" |
            awk '/^Total/ {print; exit}')

        UTIL=$(echo "$TOTAL" | awk '{print $2}' | tr -d '%')
        OPS=$(echo "$TOTAL" | awk '{print $3}')
        SECS=$(echo "$TOTAL" | awk '{print $4}')
        KOPS=$(echo "$TOTAL" | awk '{print $5}')

        # Perf index 추출
        PERF=$(echo "$RESULT" |
            awk '/Perf index/ {print $10; exit}' |
            cut -d'/' -f1)

        echo "$FIT,$TRACE_NAME,$VALID,$UTIL,$OPS,$SECS,$KOPS,$PERF" >> "$OUTPUT"
    done
done

echo ""
echo "========================================"
echo "모든 테스트 완료"
echo "결과 파일: $OUTPUT"
echo "========================================"