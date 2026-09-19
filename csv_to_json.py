import os
import sys
import csv
import json

input_file = "sample.csv" if not os.path.exists("data.csv") else "data.csv"
output_file = "output.json"

if not os.path.exists(input_file):
    with open(input_file, "w", encoding="utf-8") as f:
        f.write("name,age,city\nAlice,30,New York\nBob,25,San Francisco\n")

with open(input_file, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

json_data = json.dumps(rows, indent=2)
print(json_data)
