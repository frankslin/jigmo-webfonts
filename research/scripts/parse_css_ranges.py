#!/usr/bin/env python3
"""Parse a Google Fonts CSS2 response and find @font-face blocks whose
unicode-range covers a given set of codepoints. Prints matching blocks.
"""
import re
import sys


def parse_font_faces(css_text):
    blocks = re.findall(r"@font-face\s*\{([^}]*)\}", css_text, re.S)
    faces = []
    for b in blocks:
        m_url = re.search(r"src:\s*url\(([^)]+)\)", b)
        m_range = re.search(r"unicode-range:\s*([^;]+);", b)
        m_weight = re.search(r"font-weight:\s*([^;]+);", b)
        m_style = re.search(r"font-style:\s*([^;]+);", b)
        m_family = re.search(r"font-family:\s*'([^']+)'", b)
        if not (m_url and m_range):
            continue
        ranges = []
        for part in m_range.group(1).split(","):
            part = part.strip()
            if "-" in part:
                lo, hi = part[2:].split("-")
                ranges.append((int(lo, 16), int(hi, 16)))
            else:
                cp = int(part[2:], 16)
                ranges.append((cp, cp))
        faces.append({
            "family": m_family.group(1) if m_family else None,
            "weight": m_weight.group(1) if m_weight else None,
            "style": m_style.group(1) if m_style else None,
            "url": m_url.group(1).strip(),
            "ranges": ranges,
            "range_raw": m_range.group(1).strip(),
        })
    return faces


def codepoint_in_ranges(cp, ranges):
    return any(lo <= cp <= hi for lo, hi in ranges)


def main():
    css_path = sys.argv[1]
    test_string = sys.argv[2] if len(sys.argv) > 2 else "ABCxyz你好臺灣漢字Hgpx"
    with open(css_path, encoding="utf-8") as f:
        css_text = f.read()
    faces = parse_font_faces(css_text)
    codepoints = sorted(set(ord(c) for c in test_string if not c.isspace()))
    print(f"# {css_path}")
    print(f"# test codepoints: {[hex(c) for c in codepoints]}")
    seen_urls = set()
    for cp in codepoints:
        matched = [f for f in faces if codepoint_in_ranges(cp, f["ranges"])]
        if not matched:
            print(f"U+{cp:04X} ({chr(cp)!r}): NO MATCH")
            continue
        for f in matched:
            tag = "NEW" if f["url"] not in seen_urls else "dup"
            seen_urls.add(f["url"])
            print(f"U+{cp:04X} ({chr(cp)!r}) [{tag}]: {f['url']}")
            print(f"    range={f['range_raw'][:120]}")


if __name__ == "__main__":
    main()
