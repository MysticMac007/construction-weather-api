#!/usr/bin/env python3
import subprocess
import time
import logging
import json

# ----- Configuration -----
API_BASE_URL = "http://127.0.0.1:5001/api/calculate"
API_KEY = "550e8400-e29b-41d4-a716-446655440000"

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("API_Test")

# ----- Helper Functions -----
def run_curl_command(command: str):
    """Run a curl command and return its stdout and stderr."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr

def extract_status_and_body(curl_output: str):
    """
    Expect the curl command to output the response body
    appended with "HTTPSTATUS:<status>".
    This function extracts the numeric status and the body.
    """
    try:
        body, status_str = curl_output.rsplit("HTTPSTATUS:", 1)
        status = int(status_str.strip())
        return status, body.strip()
    except Exception as e:
        logger.error("Failed to parse curl output: " + str(e))
        return None, curl_output

def wait_for_api(url: str, timeout: int = 30, expected_status_range: tuple = (200, 499)) -> bool:
    """Poll the given URL until a valid HTTP status is returned or timeout is reached."""
    logger.info(f"Waiting for API server to become available at {url} ...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Use curl to get just the status code.
            command = f"curl -s -o /dev/null -w '%{{http_code}}' {url}"
            output, _ = run_curl_command(command)
            status = int(output.strip())
            if expected_status_range[0] <= status <= expected_status_range[1]:
                logger.info(f"API server is up (status: {status}). Proceeding with tests.")
                return True
        except Exception:
            pass
        time.sleep(1)
    logger.error("API server did not become available in time.")
    return False

# ----- Test Cases -----
# Note: Inside the JSON strings, we double all inner curly braces ({{ and }}) so that .format() does not misinterpret them.
TESTS = [
    {
        "name": "Exact Pour: Valid Request",
        "description": "A valid exact pour request.",
        "curl": (
            "curl -s -w \"HTTPSTATUS:%{{http_code}}\" -X POST \"{base_url}/exact_pour\" "
            "-H \"accept: */*\" -H \"X-API-Key: {api_key}\" -H \"Content-Type: application/json\" "
            "-d '{{\"concrete_type\": \"Type I\", \"custom_concrete\": {{\"base_curing_hours\": 22}}, "
            "\"latitude\": 38.5816, \"longitude\": -121.4944, \"pour_time\": \"2025-03-09 07:30\", "
            "\"timezone\": \"America/Los_Angeles\"}}'"
        ),
        "expected_status": 200
    },
    {
        "name": "Exact Pour: Invalid Date Format",
        "description": "Request with an incorrect date format.",
        "curl": (
            "curl -s -w \"HTTPSTATUS:%{{http_code}}\" -X POST \"{base_url}/exact_pour\" "
            "-H \"accept: */*\" -H \"X-API-Key: {api_key}\" -H \"Content-Type: application/json\" "
            "-d '{{\"concrete_type\": \"Type I\", \"custom_concrete\": {{\"base_curing_hours\": 22}}, "
            "\"latitude\": 38.5816, \"longitude\": -121.4944, \"pour_time\": \"2025/03/09\", "
            "\"timezone\": \"America/Los_Angeles\"}}'"
        ),
        "expected_status": 400
    },
    {
        "name": "Exact Pour: Past Date",
        "description": "Request with a date in the past.",
        "curl": (
            "curl -s -w \"HTTPSTATUS:%{{http_code}}\" -X POST \"{base_url}/exact_pour\" "
            "-H \"accept: */*\" -H \"X-API-Key: {api_key}\" -H \"Content-Type: application/json\" "
            "-d '{{\"concrete_type\": \"Type I\", \"custom_concrete\": {{\"base_curing_hours\": 22}}, "
            "\"latitude\": 38.5816, \"longitude\": -121.4944, \"pour_time\": \"2020-01-01 07:30\", "
            "\"timezone\": \"America/Los_Angeles\"}}'"
        ),
        "expected_status": 200
    },
    {
        "name": "Exact Pour: Out-of-Range Future Date",
        "description": "Request with a future date beyond the allowed range.",
        "curl": (
            "curl -s -w \"HTTPSTATUS:%{{http_code}}\" -X POST \"{base_url}/exact_pour\" "
            "-H \"accept: */*\" -H \"X-API-Key: {api_key}\" -H \"Content-Type: application/json\" "
            "-d '{{\"concrete_type\": \"Type I\", \"custom_concrete\": {{\"base_curing_hours\": 22}}, "
            "\"latitude\": 38.5816, \"longitude\": -121.4944, \"pour_time\": \"2025-03-16 07:30\", "
            "\"timezone\": \"America/Los_Angeles\"}}'"
        ),
        "expected_status": 400
    },
    {
        "name": "Exact Pour: Missing API Key",
        "description": "Exact pour request missing the API key.",
        "curl": (
            "curl -s -w \"HTTPSTATUS:%{{http_code}}\" -X POST \"{base_url}/exact_pour\" "
            "-H \"accept: */*\" -H \"Content-Type: application/json\" "
            "-d '{{\"concrete_type\": \"Type I\", \"custom_concrete\": {{\"base_curing_hours\": 22}}, "
            "\"latitude\": 38.5816, \"longitude\": -121.4944, \"pour_time\": \"2025-03-09 07:30\", "
            "\"timezone\": \"America/Los_Angeles\"}}'"
        ),
        "expected_status": 401
    },
    {
        "name": "Exact Pour: Malformed JSON",
        "description": "Request with a malformed JSON payload.",
        "curl": (
            "curl -s -w \"HTTPSTATUS:%{{http_code}}\" -X POST \"{base_url}/exact_pour\" "
            "-H \"accept: */*\" -H \"X-API-Key: {api_key}\" -H \"Content-Type: application/json\" "
            "-d '{{\"latitude\": 38.5816, \"longitude\": -121.4944, \"pour_time\": \"2025-03-09 07:30\", "
            "\"concrete_type\": \"Type I\", \"timezone\": \"America/Los_Angeles\"'"
        ),
        "expected_status": 400
    },
    {
        "name": "Best Pour: Valid Date Range",
        "description": "Best pour request with a valid date range.",
        "curl": (
            "curl -s -w \"HTTPSTATUS:%{{http_code}}\" -X POST \"{base_url}/best_pour\" "
            "-H \"accept: */*\" -H \"X-API-Key: {api_key}\" -H \"Content-Type: application/json\" "
            "-d '{{\"latitude\": 38.5816, \"longitude\": -121.4944, \"start_date\": \"2025-03-07\", "
            "\"end_date\": \"2025-03-09\", \"concrete_type\": \"Type I\", \"timezone\": \"America/Los_Angeles\"}}'"
        ),
        "expected_status": 200
    },
    {
        "name": "Best Pour: Invalid Date Format",
        "description": "Best pour with an invalid date format.",
        "curl": (
            "curl -s -w \"HTTPSTATUS:%{{http_code}}\" -X POST \"{base_url}/best_pour\" "
            "-H \"accept: */*\" -H \"X-API-Key: {api_key}\" -H \"Content-Type: application/json\" "
            "-d '{{\"latitude\": 38.5816, \"longitude\": -121.4944, \"request_date\": \"2025/03/07\", "
            "\"concrete_type\": \"Type I\", \"timezone\": \"America/Los_Angeles\"}}'"
        ),
        "expected_status": 400
    },
    {
        "name": "Best Pour: Missing API Key",
        "description": "Best pour request missing the API key.",
        "curl": (
            "curl -s -w \"HTTPSTATUS:%{{http_code}}\" -X POST \"{base_url}/best_pour\" "
            "-H \"accept: */*\" -H \"Content-Type: application/json\" "
            "-d '{{\"latitude\": 38.5816, \"longitude\": -121.4944, \"start_date\": \"2025-03-07\", "
            "\"end_date\": \"2025-03-09\", \"concrete_type\": \"Type I\", \"timezone\": \"America/Los_Angeles\"}}'"
        ),
        "expected_status": 401
    },
    {
        "name": "Roofing Weather: Valid Request",
        "description": "Roofing weather valid request.",
        "curl": (
            "curl -s -w \"HTTPSTATUS:%{{http_code}}\" -X POST \"{base_url}/roofing_weather\" "
            "-H \"accept: */*\" -H \"X-API-Key: {api_key}\" -H \"Content-Type: application/json\" "
            "-d '{{\"custom_roofing\": {{\"max_temp\": 30, \"min_temp\": 5, \"rain_tolerance_hours\": 8}}, "
            "\"latitude\": 38.5816, \"longitude\": -121.4944, \"roofing_type\": \"Asphalt Shingles\", "
            "\"start_time\": \"2025-03-08 07:30\", \"timezone\": \"America/Los_Angeles\"}}'"
        ),
        "expected_status": 200
    },
    {
        "name": "Roofing Weather: Missing start_time",
        "description": "Roofing weather request missing the start_time field.",
        "curl": (
            "curl -s -w \"HTTPSTATUS:%{{http_code}}\" -X POST \"{base_url}/roofing_weather\" "
            "-H \"accept: */*\" -H \"X-API-Key: {api_key}\" -H \"Content-Type: application/json\" "
            "-d '{{\"custom_roofing\": {{\"max_temp\": 30, \"min_temp\": 5, \"rain_tolerance_hours\": 8}}, "
            "\"latitude\": 38.5816, \"longitude\": -121.4944, \"roofing_type\": \"Asphalt Shingles\", "
            "\"timezone\": \"America/Los_Angeles\"}}'"
        ),
        "expected_status": 400
    },
    {
        "name": "Roofing Weather: Invalid API Key",
        "description": "Roofing weather request with an invalid API key.",
        "curl": (
            "curl -s -w \"HTTPSTATUS:%{{http_code}}\" -X POST \"{base_url}/roofing_weather\" "
            "-H \"accept: */*\" -H \"X-API-Key: invalid\" -H \"Content-Type: application/json\" "
            "-d '{{\"custom_roofing\": {{\"max_temp\": 30, \"min_temp\": 5, \"rain_tolerance_hours\": 8}}, "
            "\"latitude\": 38.5816, \"longitude\": -121.4944, \"roofing_type\": \"Asphalt Shingles\", "
            "\"start_time\": \"2025-03-08 07:30\", \"timezone\": \"America/Los_Angeles\"}}'"
        ),
        "expected_status": 401
    }
]

# ----- Test Runner -----
def run_tests():
    results = []
    for test in TESTS:
        logger.info(f"Running test: {test['name']}")
        logger.info(f"Description: {test['description']}")
        logger.info(f"Payload (curl command): {test['curl'].format(base_url=API_BASE_URL, api_key=API_KEY)}")
        command = test['curl'].format(base_url=API_BASE_URL, api_key=API_KEY)
        output, err = run_curl_command(command)
        status, body = extract_status_and_body(output)
        result = {
            "name": test["name"],
            "description": test["description"],
            "expected": test["expected_status"],
            "got": status,
            "body": body,
            "error": err
        }
        results.append(result)
        if status == test["expected_status"]:
            logger.info(f"Test '{test['name']}': PASSED")
        else:
            logger.error(f"Test '{test['name']}': FAILED")
            logger.error("----- Detailed Failure Information -----")
            logger.error(f"Expected Status: {test['expected_status']}, Got: {status}")
            logger.error(f"Response Body:\n{body}")
            logger.error(f"Request (curl):\n{command}")
            logger.error("-----------------------------------------")
    return results

def print_summary(results):
    total = len(results)
    passed = sum(1 for r in results if r["got"] == r["expected"])
    failed = total - passed
    print("\n======================================")
    print("API Test Summary")
    print("======================================")
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    if failed > 0:
        print("\nFailed Tests Details:")
        for r in results:
            if r["got"] != r["expected"]:
                print(f"Test: {r['name']}")
                print(f"Expected Status: {r['expected']}, Got: {r['got']}")
                print(f"Response Body:\n{r['body']}")
                print(f"Curl Command:\n{r['name']}")  # You can replace with r['curl'] if needed
                print("-----------------------------------------")
    else:
        print("All tests passed!")

# ----- Main Execution -----
def main():
    print("--------------------------------------")
    print("Starting API Tests")
    print("--------------------------------------")
    # Wait for the API server to be available
    poll_url = f"{API_BASE_URL}/exact_pour"
    if not wait_for_api(poll_url):
        print("API server not available. Exiting.")
        return
    results = run_tests()
    print_summary(results)
    # Optionally, write detailed results to a JSON file
    with open("api_test_summary.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
    print("\nProcess finished with exit code 0")

if __name__ == "__main__":
    main()
