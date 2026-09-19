import csv
import json
import sys
import io


def csv_to_json(csv_input: str) -> list:
    """
    Convert CSV data in a string to a list of dictionaries.
    
    Args:
        csv_input: A string containing CSV data.
        
    Returns:
        A list of dictionaries, where each dictionary represents a row
        from the CSV file.
    """
    data = []
    # Use io.StringIO to wrap the string as a file-like object
    csv_file = io.StringIO(csv_input)
    reader = csv.DictReader(csv_file)
    for row in reader:
        data.append(row)
    return data


def json_to_csv(json_data: list) -> str:
    """
    Convert a list of dictionaries (typically from JSON) to CSV format.
    
    Args:
        json_data: A list of dictionaries.
        
    Returns:
        A string containing CSV data.
    """
    if not json_data:
        return ""
    
    fieldnames = list(json_data[0].keys())
    output_string_io = io.StringIO()
    writer = csv.DictWriter(output_string_io, fieldnames=fieldnames)
    writer.writeheader()
    for row in json_data:
        writer.writerow(row)
    return output_string_io.getvalue()


def convert_csv_to_json_string(csv_input: str, indent: int = 2) -> str:
    """
    Convert CSV data in a string to a JSON string.
    
    Args:
        csv_input: A string containing CSV data.
        indent: The number of spaces for indentation in the JSON output.
        
    Returns:
        A JSON-formatted string.
    """
    data = csv_to_json(csv_input)
    return json.dumps(data, indent=indent)


def main():
    """
    Main function to demonstrate CSV to JSON conversion.
    Reads from stdin or uses sample data if no input is provided.
    """
    # Sample CSV data for demonstration purposes
    sample_csv = """name,age,city
Alice,30,New York
Bob,25,Los Angeles
Charlie,35,Chicago
"""
    
    # Check if there's input from stdin
    if not sys.stdin.isatty():
        # Read CSV data from stdin
        csv_data = sys.stdin.read()
    else:
        # Use sample data
        csv_data = sample_csv
    
    # Convert CSV to JSON
    json_output = convert_csv_to_json_string(csv_data)
    
    # Print the JSON result
    print(json_output)


if __name__ == "__main__":
    main()