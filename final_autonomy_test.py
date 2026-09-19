import os
import csv
import json

csv_file = "employees.csv"
output_file = "department_report.json"

if not os.path.exists(csv_file):
    with open(csv_file, "w", encoding="utf-8") as f:
        f.write("name,department,salary\nAlice,Engineering,95000\nBob,Engineering,85000\nCharlie,Marketing,70000\nDiana,Marketing,75000\nEve,Sales,60000\n")

dept_salaries = {}
with open(csv_file, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        dept = row["department"]
        salary = float(row["salary"])
        dept_salaries.setdefault(dept, []).append(salary)

report = {}
for dept, salaries in dept_salaries.items():
    report[dept] = round(sum(salaries) / len(salaries), 2)

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print("Department Salary Report:")
print(json.dumps(report, indent=2))
