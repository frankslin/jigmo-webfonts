#!/usr/bin/env python3
"""Extract key OS/2/hhea/head/BASE/name fields from a set of ttx XML dumps
(as produced by `ttx -q -t OS/2 -t hhea -t BASE -t head -t name -t cmap`)
and print/save a comparison table.
"""
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET

FIELDS = [
    ("head", "unitsPerEm"),
    ("hhea", "ascent"),
    ("hhea", "descent"),
    ("hhea", "lineGap"),
    ("OS/2", "sTypoAscender"),
    ("OS/2", "sTypoDescender"),
    ("OS/2", "sTypoLineGap"),
    ("OS/2", "usWinAscent"),
    ("OS/2", "usWinDescent"),
    ("OS/2", "fsSelection"),
    ("OS/2", "sCapHeight"),
    ("OS/2", "sxHeight"),
    ("OS/2", "version"),
]

TAGMAP = {"head": "head", "hhea": "hhea", "OS/2": "OS_2"}


def get_field(root, table, field):
    tag = TAGMAP.get(table, table)
    el = root.find(tag)
    if el is None:
        return None
    sub = el.find(field)
    if sub is None:
        return None
    return sub.get("value")


def has_base(root):
    return root.find("BASE") is not None


def base_summary(root):
    base = root.find("BASE")
    if base is None:
        return None
    out = []
    for axis_name in ["HorizAxis", "VertAxis"]:
        axis = base.find(axis_name)
        if axis is None:
            out.append(f"{axis_name}=None")
            continue
        bstl = axis.find("BaseTagList")
        tags = []
        if bstl is not None:
            tags = [t.get("value") for t in bstl.findall("BaselineTag")]
        bsl = axis.find("BaseScriptList")
        script_info = {}
        if bsl is not None:
            for rec in bsl.findall("BaseScriptRecord"):
                tag_el = rec.find("BaseScriptTag")
                tag = tag_el.get("value") if tag_el is not None else None
                bs = rec.find("BaseScript")
                vals = []
                default_idx = None
                if bs is not None:
                    bvs = bs.find("BaseValues")
                    if bvs is not None:
                        di = bvs.find("DefaultIndex")
                        default_idx = di.get("value") if di is not None else None
                        for c in bvs.findall("BaseCoord"):
                            coord = c.find("Coordinate")
                            vals.append(coord.get("value") if coord is not None else None)
                script_info[tag] = {"defaultBaselineTag": tags[int(default_idx)] if default_idx is not None and tags else None,
                                     "coords": vals}
        out.append(f"{axis_name}: tags={tags} scripts={script_info}")
    return " | ".join(out)


def name_field(root, name_id):
    name_tbl = root.find("name")
    if name_tbl is None:
        return None
    vals = set()
    for rec in name_tbl.findall("namerecord"):
        if rec.get("nameID") == str(name_id):
            vals.add((rec.text or "").strip())
    return "; ".join(sorted(vals)) if vals else None


def cmap_count(root):
    cmap = root.find("cmap")
    if cmap is None:
        return None
    total = 0
    subtables = []
    for sub in cmap.findall("cmap_format_4") + cmap.findall("cmap_format_12"):
        n = len(sub.findall("map"))
        subtables.append((sub.tag, sub.get("platformID"), sub.get("platEncID"), n))
    return subtables


def fs_selection_bits(rawval):
    if rawval is None:
        return None
    bitstr = rawval.replace(" ", "")
    v = int(bitstr, 2)
    bits = []
    names = {0: "ITALIC", 5: "BOLD", 6: "REGULAR", 7: "USE_TYPO_METRICS",
             8: "WWS", 9: "OBLIQUE"}
    for b, n in names.items():
        if v & (1 << b):
            bits.append(n)
    return f"0x{v:04X} ({','.join(bits) if bits else 'none'})"


def main():
    ttx_dir = sys.argv[1] if len(sys.argv) > 1 else "work/ttx-dumps"
    files = sorted(glob.glob(os.path.join(ttx_dir, "*.ttx")))
    rows = []
    for path in files:
        name = os.path.basename(path)[:-4]
        root = ET.parse(path).getroot()
        row = {"file": name}
        for table, field in FIELDS:
            row[f"{table}.{field}"] = get_field(root, table, field)
        row["OS/2.fsSelection_decoded"] = fs_selection_bits(row.get("OS/2.fsSelection"))
        row["BASE.present"] = has_base(root)
        row["BASE.summary"] = base_summary(root)
        row["name.family(1)"] = name_field(root, 1)
        row["name.subfamily(2)"] = name_field(root, 2)
        row["name.full(4)"] = name_field(root, 4)
        row["name.postscript(6)"] = name_field(root, 6)
        row["name.version(5)"] = name_field(root, 5)
        row["cmap.subtables"] = cmap_count(root)
        rows.append(row)

    cols = ["file"] + [f"{t}.{f}" for t, f in FIELDS] + [
        "OS/2.fsSelection_decoded", "BASE.present",
        "name.family(1)", "name.subfamily(2)", "name.full(4)",
        "name.postscript(6)", "name.version(5)",
    ]

    out_tsv = os.path.join("data", "metrics.tsv")
    with open(out_tsv, "w", encoding="utf-8") as f:
        f.write("\t".join(cols) + "\n")
        for row in rows:
            f.write("\t".join(str(row.get(c, "")) for c in cols) + "\n")
    print(f"Wrote {out_tsv}", file=sys.stderr)

    # Print a readable version to stdout too
    for row in rows:
        print(f"--- {row['file']} ---")
        for c in cols[1:]:
            print(f"  {c}: {row.get(c)}")
        print(f"  BASE.summary: {row['BASE.summary']}")
        print(f"  cmap.subtables: {row['cmap.subtables']}")
        print()


if __name__ == "__main__":
    main()
