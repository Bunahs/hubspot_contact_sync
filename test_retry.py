
from unittest.mock import Mock, patch

import requests

from src.sync_contacts import retry_request


def test_retry():

    # Giả lập lỗi HTTP 500
    error_response = Mock()
    error_response.status_code = 500
    error_response.headers = {}

    error = requests.exceptions.HTTPError(
        "500 Server Error",
        response=error_response
    )

    # Giả lập phản hồi thành công
    success_response = Mock()
    success_response.raise_for_status.return_value = None

    # Lần 1 lỗi, lần 2 thành công
    with patch(
        "src.sync_contacts.requests.request",
        side_effect=[error, success_response]
    ) as mock_request:

        with patch("src.sync_contacts.time.sleep") as mock_sleep:

            response = retry_request(
                "GET",
                "https://example.com/test",
                timeout=30
            )

    # Kiểm tra
    assert response == success_response
    assert mock_request.call_count == 2
    mock_sleep.assert_called_once_with(1)

    print("Retry test passed!")
    print("Total API attempts:", mock_request.call_count)


if __name__ == "__main__":
    test_retry()
