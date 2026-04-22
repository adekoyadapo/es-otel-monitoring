#!/usr/bin/env python3

import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        print("usage: convert_saved_objects_export_json.py <input-export.json> <output.ndjson>", file=sys.stderr)
        raise SystemExit(2)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    with input_path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)

    objects = payload.get("objects")
    if not isinstance(objects, list):
        print("input file does not contain an objects array", file=sys.stderr)
        raise SystemExit(1)

    with output_path.open("w", encoding="utf-8") as fh:
        for obj in objects:
            fh.write(json.dumps(obj, separators=(",", ":")))
            fh.write("\n")


if __name__ == "__main__":
    main()
