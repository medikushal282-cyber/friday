import csv
import json
import sys
import os

def csv_to_json(csv_file_path, output_file_path=None):
    """
    Convert a CSV file to JSON using Python's standard library.
    
    Args:
        csv_file_path: Path to the input CSV file.
        output_file_path: Optional path to write JSON output. If not provided, prints to stdout.
    
    Returns:
        JSON-formatted string.
    """
    with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
        data = list(csv.DictReader(csvfile))
    
    json_str = json.dumps(data, indent=4)
    
    if output_file_path:
        with open(output_file_path, 'w', encoding='utf-8') as jsonfile:
            jsonfile.write(json_str)
    else:
        print(json_str)
    
    return json_str

def create_sample_csv(filename='sample_csv.csv'):
    """Create a sample CSV file for testing purposes."""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'name', 'department', 'salary'])
        writer.writerow([1, 'Alice Johnson', 'Engineering', 95000])
        writer.writerow([2, 'Bob Smith', 'Marketing', 72000])
        writer.writerow([3, 'Carol Williams', 'Engineering', 88000])
        writer.writerow([4, 'David Brown', 'HR', 65000])

def main():
    """Main function to demonstrate CSV to JSON conversion."""
    sample_csv_file = 'sample_csv.csv'
    output_json_file = 'output.json'
    
    # Check if sample CSV exists, create it if not
    if not os.path.exists(sample_csv_file):
        create_sample_csv(sample_csv_file)
        print(f"[INFO] Created sample CSV file: {sample_csv_file}")
    
    # Convert CSV to JSON and print to stdout
    print("[INFO] Converting CSV to JSON...")
    json_str = csv_to_json(sample_csv_file)
    
    # Also save to a file for demonstration
    print(f"\n[INFO] Writing JSON output to file: {output_json_file}")
    csv_to_json(sample_csv_file, output_json_file)
    
    print(f"\n[INFO] Conversion complete. JSON output:")
    print(json_str)

if __name__ == '__main__':
    main()