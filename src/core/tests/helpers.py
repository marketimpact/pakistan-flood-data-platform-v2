"""Helper functions for testing."""

from unittest.mock import Mock
import json


def mock_api_response(status_code, json_data=None, headers=None):
    """
    Create a mock response object that mimics requests.Response.

    Args:
        status_code: HTTP status code
        json_data: JSON data to return (dict or None)
        headers: Optional headers dict

    Returns:
        Mock response object
    """
    response = Mock()
    response.status_code = status_code
    response.headers = headers or {}

    if json_data is not None:
        response.json.return_value = json_data
        response.text = json.dumps(json_data)
    else:
        response.json.side_effect = ValueError("No JSON content")
        response.text = ""

    # Add common response attributes
    response.ok = 200 <= status_code < 400
    response.raise_for_status = Mock()
    if not response.ok:
        response.raise_for_status.side_effect = Exception(f"HTTP {status_code} error")

    return response


def mock_api_sequence(*responses):
    """
    Create a sequence of mock responses for multiple API calls.

    Args:
        *responses: Tuples of (status_code, json_data) or (status_code, json_data, headers)

    Returns:
        List of mock response objects
    """
    mock_responses = []

    for response_args in responses:
        if len(response_args) == 2:
            status_code, json_data = response_args
            headers = None
        elif len(response_args) == 3:
            status_code, json_data, headers = response_args
        else:
            raise ValueError(
                "Each response must be (status_code, json_data) or (status_code, json_data, headers)"
            )

        mock_responses.append(mock_api_response(status_code, json_data, headers))

    return mock_responses


def mock_requests_get(side_effect=None, return_value=None):
    """
    Create a mock for requests.get with common configurations.

    Args:
        side_effect: List of responses or exception to raise
        return_value: Single response to always return

    Returns:
        Configured Mock object
    """
    mock_get = Mock()

    if side_effect is not None:
        mock_get.side_effect = side_effect
    elif return_value is not None:
        mock_get.return_value = return_value

    return mock_get


def assert_api_called_with(mock_get, expected_url, expected_headers=None, call_index=0):
    """
    Assert that a mocked requests.get was called with expected parameters.

    Args:
        mock_get: Mocked requests.get
        expected_url: Expected URL (can be partial)
        expected_headers: Expected headers dict (optional)
        call_index: Which call to check (default: 0)
    """
    assert (
        mock_get.call_count > call_index
    ), f"Expected at least {call_index + 1} calls, got {mock_get.call_count}"

    actual_call = mock_get.call_args_list[call_index]
    actual_url = actual_call[0][0] if actual_call[0] else actual_call[1].get("url", "")

    assert (
        expected_url in actual_url
    ), f"Expected URL to contain '{expected_url}', got '{actual_url}'"

    if expected_headers:
        actual_headers = actual_call[1].get("headers", {})
        for key, value in expected_headers.items():
            assert (
                actual_headers.get(key) == value
            ), f"Expected header '{key}' to be '{value}', got '{actual_headers.get(key)}'"
