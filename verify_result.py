import os

def verify():
    # Check if factorial.py exists
    if not os.path.exists('factorial.py'):
        print("Error: factorial.py does not exist")
        return False

    # Run factorial.py and capture output
    import subprocess
    try:
        result = subprocess.run(['python', 'factorial.py'], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running factorial.py: {result.stderr}")
            return False

        output = result.stdout.strip()

        # The expected factorial of 5 is 120
        expected = 120
        if str(expected) in output:
            print(f"Verification successful: factorial(5) = {expected} found in output: '{output}'")
            return True
        else:
            print(f"Verification failed: expected '{expected}' in output, but got: '{output}'")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == '__main__':
    verify()