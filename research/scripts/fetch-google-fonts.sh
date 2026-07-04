#!/usr/bin/env bash
# Fetch Google Fonts CSS2 responses for Noto Serif/Sans TC/SC (wght 400) and
# download every .woff2 referenced in each CSS file.
#
# Usage: ./fetch-google-fonts.sh
#
# Outputs:
#   research/data/google-<family>.css        (raw CSS response)
#   research/fonts/google/<family>/*.woff2    (every referenced woff2)
#   research/data/urls.tsv                    (url \t local_path \t family)
set -euo pipefail
cd "$(dirname "$0")/.."   # -> research/

UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

mkdir -p data fonts/google

FAMILIES=(
  "Noto+Serif+TC:google-noto-serif-tc"
  "Noto+Sans+TC:google-noto-sans-tc"
  "Noto+Serif+SC:google-noto-serif-sc"
  "Noto+Sans+SC:google-noto-sans-sc"
)

: > data/urls.tsv
echo -e "url\tlocal_path\tfamily_slug" >> data/urls.tsv

for pair in "${FAMILIES[@]}"; do
  fam="${pair%%:*}"
  slug="${pair##*:}"
  css="data/${slug}.css"
  echo "== Fetching CSS for $fam ==" >&2
  curl -sL "https://fonts.googleapis.com/css2?family=${fam}:wght@400&display=swap" \
    -H "User-Agent: $UA" -o "$css"

  outdir="fonts/google/${slug}"
  mkdir -p "$outdir"

  urls=$(grep -oE 'https://fonts\.gstatic\.com/[^)]+\.woff2' "$css" | sort -u)
  n=$(echo "$urls" | wc -l)
  echo "  $n unique woff2 urls" >&2

  i=0
  while IFS= read -r url; do
    i=$((i+1))
    fname=$(basename "$url")
    dest="${outdir}/${fname}"
    if [ ! -s "$dest" ]; then
      curl -sL "$url" -o "$dest"
    fi
    echo -e "${url}\t${dest}\t${slug}" >> data/urls.tsv
  done <<< "$urls"
done

echo "Done. See data/urls.tsv" >&2
