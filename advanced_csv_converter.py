#!/usr/bin/env python3
"""
advanced_csv_converter.py
==========================
Converts a CSV file to pretty-printed JSON using only the Python standard library.

- Reads CSV rows using csv.DictReader
- Preserves CSV headers as JSON object keys
- Writes pretty-printed JSON using json.dump (indent=2, ensure_ascii=False)
- Accepts input and output file paths through argparse
- Handles UTF-8 files correctly
- Reports a clear error when the input CSV does not exist
"""

import argparse
import csv
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a CSV file to pretty-printed JSON."
    )
    parser.add_argument("input", help="Path to the input CSV file")
    parser.add_argument("output", help="Path to the output JSON file")
    return parser.parse_args()


def csv_to_json(input_path: str, output_path: str) -> None:
    """
    Read a CSV file and write its contents as a JSON array of objects.
    Each row becomes an object keyed by the CSV column headers.
    """
    in_path = Path(input_path)

    # Check that the input file exists and report a clear error if not
    if not in_path.exists():
        print(f"Error: Input CSV file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Read all rows as dictionaries
    rows = []
    try:
        with open(in_path, mode='r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except csv.Error as e:
        print(f"Error: Failed to parse CSV file '{input_path}': {e}", file=sys.stderr)
        sys.exit(1)

    # Write pretty-printed JSON
    try:
        with open(output_path, mode='w', encoding='utf-8') as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)
    except (IOError, OSError) as e:
        print(f"Error: Failed to write JSON file '{output_path}': {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Successfully converted '{input_path}' to '{output_path}' ({len(rows)} rows)")


def main() -> None:
    args = parse_args()
    csv_to_json(args.input, args.output)


if __name__ == "__main__":
    main()