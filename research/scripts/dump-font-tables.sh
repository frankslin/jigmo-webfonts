#!/usr/bin/env bash
# For every font in research/work/rep/, list its SFNT tables (ttx -l) and
# build a presence matrix (data/tables.tsv) for the tables the research
# task cares about.
set -euo pipefail
cd "$(dirname "$0")/.."   # -> research/

REPDIR="work/rep"
CHECK_TABLES=(OS/2 hhea BASE vhea vmtx name cmap head maxp GSUB GPOS GDEF STAT glyf loca CFF prep gasp fpgm cvt DSIG VORG)

mkdir -p work
: > work/ttx-list-full.txt

declare -A PRESENT
FILES=()
for f in "$REPDIR"/*; do
  fname=$(basename "$f")
  FILES+=("$fname")
  echo "=== $fname ===" >> work/ttx-list-full.txt
  ttx -l "$f" >> work/ttx-list-full.txt 2>&1
  tags=$(ttx -l "$f" 2>&1 | tail -n +4 | awk '{print $1}')
  for t in "${CHECK_TABLES[@]}"; do
    if echo "$tags" | grep -qxF "$t"; then
      PRESENT["$fname|$t"]=1
    else
      PRESENT["$fname|$t"]=0
    fi
  done
done

{
  printf "file"
  for t in "${CHECK_TABLES[@]}"; do printf "\t%s" "$t"; done
  printf "\n"
  for fname in "${FILES[@]}"; do
    printf "%s" "$fname"
    for t in "${CHECK_TABLES[@]}"; do
      printf "\t%s" "${PRESENT["$fname|$t"]}"
    done
    printf "\n"
  done
} > data/tables.tsv

echo "Wrote data/tables.tsv" >&2
column -t -s$'\t' data/tables.tsv
