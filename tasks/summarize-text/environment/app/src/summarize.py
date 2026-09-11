#!/usr/bin/env python3
"""Word-count summariser.

Usage: summarize.py --data <dir> --out <file>
"""

import argparse
import json
from pathlib import Path


def summarize(data_dir):
    entries = []
    for path in Path(data_dir).glob("*.txt"):
        if not path.is_file():
            continue
        entries.append({"name": path.name, "words": len(path.read_text().split())})
    return {"files": entries, "total_words": len(entries)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    report = summarize(args.data)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
