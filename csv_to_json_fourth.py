import csv
import json
import os

def csv_to_json(csv_filename, json_filename):
    """
    Convert a CSV file to a JSON file using standard library modules.
    
    Args:
        csv_filename (str): Path to the input CSV file.
        json_filename (str): Path to the output JSON file.
    """
    with open(csv_filename, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        data = list(reader)
        
    with open(json_filename, 'w', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile, indent=4, ensure_ascii=False)
        
    return data

def generate_sample_csv(filename, data_rows, headers):
    """
    Generate a sample CSV file for testing.
    
    Args:
        filename (str): Path to the CSV file to create.
        data_rows (list of lists): Data to write to CSV.
        headers (list of str): Column headers.
    """
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(data_rows)

def main():
    # Setup test files
    csv_file = 'sample_data.csv'
    json_file = 'sample_data.json'
    
    # Define sample data
    headers = ['name', 'age', 'city']
    rows = [
        ['Alice', '30', 'New York'],
        ['Bob', '25', 'Los Angeles'],
        ['Charlie', '35', 'Chicago']
    ]
    
    # Generate sample CSV
    generate_sample_csv(csv_file, rows, headers)
    
    # Convert to JSON
    try:
        data = csv_to_json(csv_file, json_file)
        print("Conversion successful!")
        print(f"CSV file: {csv_file}")
        print(f"JSON file: {json_file}")
        print()
        print("JSON Content:")
        print(json.dumps(data, indent=4, ensure_ascii=False))
    except Exception as e:
        print(f"Error during conversion: {e}")
    finally:
        # Clean up temporary files
        if os.path.exists(csv_file):
            os.remove(csv_file)
        if os.path.exists(json_file):
            os.remove(json_file)

if __name__ == '__main__':
    main()