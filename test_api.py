#!/usr/bin/env python3
import requests
import json
import time

# Base URL and headers
BASE_URL = "http://127.0.0.1:5001/api/calculate"
API_KEY = "550e8400-e29b-41d4-a716-446655440000"
DEFAULT_HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json",
    "accept": "*/*"
}

# List of test cases
tests = [
    {
        "name": "Exact Pour: Valid Request",
        "endpoint": "/exact_pour",
        "payload": {
            "concrete_type": "Type I",
            "custom_concrete": {"base_curing_hours": 22},
            "latitude": 38.5816,
            "longitude": -121.4944,
            "pour_time": "2025-03-09 07:30",
            "timezone": "America/Los_Angeles"
        },
        "expected_status": 200,
        "description": "A valid exact pour request."
    },
    {
        "name": "Exact Pour: Invalid Date Format",
        "endpoint": "/exact_pour",
        "payload": {
            "concrete_type": "Type I",
            "custom_concrete": {"base_curing_hours": 22},
            "latitude": 38.5816,
            "longitude": -121.4944,
            "pour_time": "2025/03/09",  # wrong format
            "timezone": "America/Los_Angeles"
        },
        "expected_status": 400,
        "description": "Exact pour with wrong date format."
    },
    {
        "name": "Exact Pour: Past Date",
        "endpoint": "/exact_pour",
        "payload": {
            "concrete_type": "Type I",
            "custom_concrete": {"base_curing_hours": 22},
            "latitude": 38.5816,
            "longitude": -121.4944,
            "pour_time": "2020-01-01 07:30",  # past date
            "timezone": "America/Los_Angeles"
        },
        "expected_status": 400,
        "description": "Exact pour with a past date."
    },
    {
        "name": "Exact Pour: Out-of-Range Future Date",
        "endpoint": "/exact_pour",
        "payload": {
            "concrete_type": "Type I",
            "custom_concrete": {"base_curing_hours": 22},
            "latitude": 38.5816,
            "longitude": -121.4944,
            "pour_time": "2025-03-16 07:30",  # more than 5 days ahead
            "timezone": "America/Los_Angeles"
        },
        "expected_status": 400,
        "description": "Exact pour with a future date beyond allowed range."
    },
    {
        "name": "Exact Pour: Missing API Key",
        "endpoint": "/exact_pour",
        "payload": {
            "concrete_type": "Type I",
            "custom_concrete": {"base_curing_hours": 22},
            "latitude": 38.5816,
            "longitude": -121.4944,
            "pour_time": "2025-03-09 07:30",
            "timezone": "America/Los_Angeles"
        },
        "headers": {  # no API key provided
            "Content-Type": "application/json",
            "accept": "*/*"
        },
        "expected_status": 401,
        "description": "Exact pour missing API key."
    },
    {
        "name": "Exact Pour: Malformed JSON",
        "endpoint": "/exact_pour",
        "raw_payload": '{"latitude":38.5816,"longitude":-121.4944,"pour_time":"2025-03-09 07:30","concrete_type":"Type I","timezone":"America/Los_Angeles"',
        # missing closing }
        "expected_status": 400,
        "description": "Exact pour with malformed JSON."
    },
    {
        "name": "Best Pour: Valid Date Range",
        "endpoint": "/best_pour",
        "payload": {
            "latitude": 38.5816,
            "longitude": -121.4944,
            "start_date": "2025-03-07",
            "end_date": "2025-03-09",
            "concrete_type": "Type I",
            "timezone": "America/Los_Angeles"
        },
        "expected_status": 200,
        "description": "Best pour valid date range request."
    },
    {
        "name": "Best Pour: Invalid Date Format",
        "endpoint": "/best_pour",
        "payload": {
            "latitude": 38.5816,
            "longitude": -121.4944,
            "request_date": "2025/03/07",  # wrong format
            "concrete_type": "Type I",
            "timezone": "America/Los_Angeles"
        },
        "expected_status": 400,
        "description": "Best pour with invalid date format."
    },
    {
        "name": "Best Pour: Missing API Key",
        "endpoint": "/best_pour",
        "payload": {
            "latitude": 38.5816,
            "longitude": -121.4944,
            "start_date": "2025-03-07",
            "end_date": "2025-03-09",
            "concrete_type": "Type I",
            "timezone": "America/Los_Angeles"
        },
        "headers": {
            "Content-Type": "application/json",
            "accept": "*/*"
        },
        "expected_status": 401,
        "description": "Best pour missing API key."
    },
    {
        "name": "Roofing Weather: Valid Request",
        "endpoint": "/roofing_weather",
        "payload": {
            "custom_roofing": {"max_temp": 30, "min_temp": 5, "rain_tolerance_hours": 8},
            "latitude": 38.5816,
            "longitude": -121.4944,
            "roofing_type": "Asphalt Shingles",
            "start_time": "2025-03-08 07:30",
            "timezone": "America/Los_Angeles"
        },
        "expected_status": 200,
        "description": "Roofing weather valid request."
    },
    {
        "name": "Roofing Weather: Missing start_time",
        "endpoint": "/roofing_weather",
        "payload": {
            "custom_roofing": {"max_temp": 30, "min_temp": 5, "rain_tolerance_hours": 8},
            "latitude": 38.5816,
            "longitude": -121.4944,
            "roofing_type": "Asphalt Shingles",
            "timezone": "America/Los_Angeles"
        },
        "expected_status": 400,
        "description": "Roofing weather missing required field start_time."
    },
    {
        "name": "Roofing Weather: Invalid API Key",
        "endpoint": "/roofing_weather",
        "payload": {
            "custom_roofing": {"max_temp": 30, "min_temp": 5, "rain_tolerance_hours": 8},
            "latitude": 38.5816,
            "longitude": -121.4944,
            "roofing_type": "Asphalt Shingles",
            "start_time": "2025-03-08 07:30",
            "timezone": "America/Los_Angeles"
        },
        "headers": {
            "X-API-Key": "invalid",
            "Content-Type": "application/json",
            "accept": "*/*"
        },
        "expected_status": 401,
        "description": "Roofing weather with invalid API key."
    }
]


def run_test(test):
    url = BASE_URL + test["endpoint"]
    headers = test.get("headers", DEFAULT_HEADERS)
    payload = test.get("payload")
    raw_payload = test.get("raw_payload")
    try:
        if raw_payload:
            response = requests.post(url, headers=headers, data=raw_payload)
        else:
            response = requests.post(url, headers=headers, json=payload)
        return response
    except Exception as e:
        return e


def main():
    results = []
    print("\n--------------------------------------")
    print("Starting API Tests")
    print("--------------------------------------\n")
    for test in tests:
        print(f"Running test: {test['name']}")
        response = run_test(test)
        if isinstance(response, Exception):
            result = {
                "name": test["name"],
                "status": "ERROR",
                "error": str(response)
            }
        else:
            passed = response.status_code == test["expected_status"]
            result = {
                "name": test["name"],
                "expected": test.get("expected_status", "N/A"),
                "got": response.status_code,
                "passed": passed,
                "response": response.text.strip()
            }
        results.append(result)
        status_text = "PASSED" if result.get("passed") else "FAILED"
        print(f"Test '{test['name']}': {status_text}")
        print("--------------------------------------------------\n")
        time.sleep(0.2)

    # Summarize results
    total = len(results)
    passed_tests = [r for r in results if r.get("passed")]
    failed_tests = [r for r in results if not r.get("passed")]

    print("======================================")
    print("API Test Summary")
    print("======================================")
    print(f"Total tests: {total}")
    print(f"Passed: {len(passed_tests)}")
    print(f"Failed: {len(failed_tests)}")
    if failed_tests:
        print("\nFailed Tests Details:")
        for ft in failed_tests:
            expected = ft.get("expected", "N/A")
            got = ft.get("got", "N/A")
            print(f"Test: {ft['name']}")
            print(f"Expected: {expected}, Got: {got}")
            print(f"Response: {ft['response']}")
            print("--------------------------------------------------")
    else:
        print("All tests passed!")


if __name__ == "__main__":
    main()
