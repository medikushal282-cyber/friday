import csv
import json
import sys


def csv_to_json(csv_file_path, indent=4):
    """
    Convert CSV data to JSON using Python's standard library.
    
    Args:
        csv_file_path: Path to the CSV file
        indent: Indentation for JSON output
    
    Returns:
        JSON-formatted string
    """
    with open(csv_file_path, newline='') as csvfile:
        data = list(csv.DictReader(csvfile))
    return json.dumps(data, indent=indent)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # If no CSV file is provided, create a sample CSV and convert it
        sample_csv = "id,name,age\n1,Alice,30\n2,Bob,25\n3,Charlie,35"
        sample_file = "sample_data.csv"
        
        with open(sample_file, 'w', newline='') as f:
            f.write(sample_csv)
        
        result = csv_to_json(sample_file)
        print(result)
    else:
        csv_file = sys.argv[1]
        result = csv_to_json(csv_file)
        print(result)