#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""zh-Hans regression gate for the MissionPlanner fork (python3 stdlib only).

Checks:
  a) translated forms  : every invariant (neutral) resx that has a zh-Hans
     sibling must have ALL visible entries (.Text/.Items/.Label/.Title/
     .Category/.Description, endswith) present and non-empty in the zh-Hans
     resx. The form set must cover the baseline snapshot.
  b) Designer migrations: every migrated .Text recorded in
     baseline/designer_migration.json must still exist as an invariant resx
     entry with the same value, with a non-empty zh-Hans counterpart.
  c) strings_zhHans.txt : every L10NU.GetString("key", ...) call site in the
     repo resolves to a key in the file; file stays UTF-8 with BOM and LF
     line endings (the file is LF by design - verified against baseline);
     every key line is well-formed key=value.
  d) statustext_zhHans.json: exists, valid JSON, entry count >= baseline.
  e) hardcoded regression: rescan user-visible literals (MessageBox.Show /
     CustomMessageBox( / .Text = "...") in the files audited in
     baseline/mp_hardcoded_remaining.json; any (ctx, string) not present in
     the baseline snapshot is a new unwrapped string -> FAIL.

Exit code 0 = pass, 1 = fail. Human-readable report on stdout.
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baseline")

VISIBLE_UV = (".Text", ".Items", ".Label", ".Title", ".Category", ".Description")
TXT_PATH = os.path.join(REPO, "ExtLibs", "Utilities", "Resources", "strings_zhHans.txt")
STATUS_JSON = os.path.join(REPO, "ExtLibs", "Utilities", "Resources", "statustext_zhHans.json")

CTX_PATTERNS = [
    ("MessageBox", re.compile(r'MessageBox\.Show\(\s*"((?:[^"\\]|\\.)+)"')),
    ("CustomMessageBox", re.compile(r'CustomMessageBox\(\s*"((?:[^"\\]|\\.)+)"')),
    (".Text", re.compile(r'\.Text\s*=\s*"((?:[^"\\]|\\.)+)"\s*;')),
]
fails = []
warns = []


def load_json(name):
    with open(os.path.join(BASE, name), encoding="utf-8") as fh:
        return json.load(fh)


def parse_resx(path):
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, FileNotFoundError):
        return None
    d = {}
    for data in root.findall("data"):
        n = data.get("name")
        v = data.find("value")
        if n and data.get("type") is None and v is not None and v.text is not None:
            d[n] = v.text
    return d


def check_forms():
    """a) visible-entry coverage of translated forms."""
    baseline_forms = load_json("forms.json")
    pairs = []
    for root_dir, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in (".git", "bin", "obj", "packages")]
        for fn in files:
            if fn.endswith(".zh-Hans.resx"):
                neu = fn[:-len(".zh-Hans.resx")] + ".resx"
                if os.path.exists(os.path.join(root_dir, neu)):
                    pairs.append(os.path.relpath(os.path.join(root_dir, fn), REPO))
    known = set(pairs) | set(baseline_forms)
    missing_forms = sorted(set(baseline_forms) - set(pairs))
    if missing_forms:
        fails.append(f"[forms] baseline zh-Hans resx no longer present: {missing_forms[:10]}")
    bad = 0
    for rel in sorted(known):
        zd = parse_resx(os.path.join(REPO, rel))
        nd = parse_resx(os.path.join(REPO, rel.replace(".zh-Hans.resx", ".resx")))
        if zd is None or nd is None:
            fails.append(f"[forms] resx parse failure: {rel}")
            bad += 1
            continue
        for n, v in nd.items():
            if not n.endswith(VISIBLE_UV):
                continue
            if not v.strip():
                continue  # neutral itself empty -> nothing to translate
            zh = zd.get(n)
            if zh is None:
                fails.append(f"[forms] missing visible entry {n} in {rel}")
                bad += 1
            elif not zh.strip():
                fails.append(f"[forms] empty zh-Hans value for {n} in {rel}")
                bad += 1
    print(f"[forms] checked {len(known)} translated zh-Hans forms "
          f"(baseline {len(baseline_forms)}): {'FAIL' if bad else 'PASS'}")
    return bad == 0


def unescape_cs(s):
    """Baseline literals were recorded with C# escapes (\\r\\n); resx stores
    the real characters."""
    return (s.replace("\\r\\n", "\n").replace("\\n", "\n")
             .replace("\\r", "\n").replace("\\t", "\t").replace('\\"', '"'))


def check_designer():
    """b) each migrated .Text still has an invariant resx entry with same value."""
    recs = load_json("designer_migration.json")
    bad = 0
    cache = {}
    for r in recs:
        if not r.get("apply"):
            continue
        dcs = r["file"]
        if not dcs.endswith(".Designer.cs"):
            continue
        resx = dcs[:-len(".Designer.cs")] + ".resx"
        resx_zh = dcs[:-len(".Designer.cs")] + ".zh-Hans.resx"
        for p, tag in ((resx, "neutral"), (resx_zh, "zh-Hans")):
            key = (p, tag)
            if key not in cache:
                cache[key] = parse_resx(os.path.join(REPO, p))
        nd = cache[(resx, "neutral")]
        zd = cache[(resx_zh, "zh-Hans")]
        k = r["resx_key"]
        if nd is None or nd.get(k) != unescape_cs(r["en"]):
            fails.append(f"[designer] {dcs}: invariant resx {resx} entry {k!r} "
                         f"value != original literal {r['en']!r}")
            bad += 1
        elif zd is None or not (zd.get(k) or "").strip():
            fails.append(f"[designer] {dcs}: zh-Hans resx {resx_zh} entry {k!r} missing/empty")
            bad += 1
    print(f"[designer] checked {sum(1 for r in recs if r.get('apply') and r['file'].endswith('.Designer.cs'))} "
          f"migrations across 21 Designer.cs: {'FAIL' if bad else 'PASS'}")
    return bad == 0


def check_strings_txt():
    """c) L10NU keys all resolve; encoding/EOL invariants."""
    bad = 0
    with open(TXT_PATH, "rb") as fh:
        raw = fh.read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    if not bom:
        fails.append("[strings] strings_zhHans.txt lost its UTF-8 BOM")
        bad += 1
    n_cr = raw.count(b"\r")
    if n_cr:
        fails.append(f"[strings] strings_zhHans.txt has {n_cr} CR bytes (must stay LF)")
        bad += 1
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        fails.append(f"[strings] strings_zhHans.txt is not valid UTF-8: {e}")
        print(f"[strings] FAIL (invalid UTF-8)")
        return False
    keys = set()
    for i, line in enumerate(text.split("\n"), 1):
        if not line or line.lstrip().startswith("#"):
            continue
        if "=" not in line:
            fails.append(f"[strings] line {i} has no '=': {line[:60]!r}")
            bad += 1
            continue
        keys.add(line.split("=", 1)[0])
    # all L10NU call sites resolve
    pat = re.compile(r'L10NU\.GetString\(\s*"((?:[^"\\]|\\.)+)"')
    n_calls = 0
    for root_dir, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in (".git", "bin", "obj", "packages")]
        for fn in files:
            if not fn.endswith(".cs"):
                continue
            p = os.path.join(root_dir, fn)
            try:
                t = open(p, "rb").read().decode("utf-8-sig", errors="replace")
            except OSError:
                continue
            for m in pat.finditer(t):
                n_calls += 1
                if m.group(1) not in keys:
                    fails.append(f"[strings] L10NU key {m.group(1)!r} missing "
                                 f"({os.path.relpath(p, REPO)})")
                    bad += 1
    print(f"[strings] {len(keys)} keys, {n_calls} L10NU call sites, "
          f"UTF-8+BOM+LF ok: {'FAIL' if bad else 'PASS'}")
    return bad == 0


def check_statustext():
    """d) statustext_zhHans.json present, valid, >= baseline count."""
    base = load_json("statustext.json")["entry_count"]
    bad = 0
    try:
        with open(STATUS_JSON, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        fails.append(f"[statustext] statustext_zhHans.json missing/invalid: {e}")
        print("[statustext] FAIL")
        return False
    n = len(data) if isinstance(data, list) else -1
    if n < base:
        fails.append(f"[statustext] entry count {n} < baseline {base}")
        bad += 1
    for i, e in enumerate(data if isinstance(data, list) else []):
        if not isinstance(e, dict) or "match" not in e or "zh" not in e:
            fails.append(f"[statustext] entry {i} malformed")
            bad += 1
            break
    print(f"[statustext] valid JSON, {n} entries (baseline {base}): {'FAIL' if bad else 'PASS'}")
    return bad == 0


def check_hardcoded():
    """e) no new unwrapped user-visible literals in audited files."""
    base_list = load_json("mp_hardcoded_remaining.json")
    scope = sorted({r["file"] for r in base_list})
    base_set = {(r["file"], r["ctx"], r["s"]) for r in base_list}
    new = []
    for f in scope:
        p = os.path.join(REPO, f)
        if f.endswith(".Designer.cs") or not os.path.exists(p):
            continue
        t = open(p, "rb").read().decode("utf-8-sig", errors="replace")
        for ctx, pat in CTX_PATTERNS:
            for m in pat.finditer(t):
                s = m.group(1)
                if not re.search(r"[A-Za-z]{2}", s):
                    continue
                if (f, ctx, s) not in base_set:
                    ln = t[: m.start()].count("\n") + 1
                    new.append({"file": f, "line": ln, "ctx": ctx, "s": s})
    # baseline entries that disappeared (fixed) are informational
    fixed = 0
    for f, ctx, s in base_set:
        p = os.path.join(REPO, f)
        if not os.path.exists(p) or f.endswith(".Designer.cs"):
            continue
        t = open(p, "rb").read().decode("utf-8-sig", errors="replace")
        if ctx == "MessageBox" and not re.search(r'MessageBox\.Show\(\s*"' + re.escape(s), t) \
           and f'"{s}"' not in t:
            fixed += 1
        elif ctx == ".Text" and not re.search(r'\.Text\s*=\s*"' + re.escape(s) + r'"\s*;', t) \
                and f'"{s}"' not in t:
            fixed += 1
    for x in new[:40]:
        fails.append(f"[hardcoded] NEW unwrapped string {x['ctx']} {x['file']}:{x['line']} {x['s'][:80]!r}")
    print(f"[hardcoded] scanned {len(scope)} audited files: new={len(new)} "
          f"(baseline={len(base_set)}, since-fixed~{fixed}): "
          f"{'FAIL' if new else 'PASS'}")
    return not new


def main():
    print("=== MP zh-Hans i18n regression gate ===")
    ok = True
    ok &= check_forms()
    ok &= check_designer()
    ok &= check_strings_txt()
    ok &= check_statustext()
    ok &= check_hardcoded()
    if fails:
        print("\nFAILURES:")
        for f in fails:
            print(f"  - {f}")
    if warns:
        print("\nWARNINGS:")
        for w in warns:
            print(f"  - {w}")
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
