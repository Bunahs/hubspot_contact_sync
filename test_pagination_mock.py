
from unittest.mock import Mock, patch

from src.sync_contacts import get_hubspot_contacts


def test_pagination():

    # Giả lập phản hồi trang 1: có 2 Contacts
    page_1 = {
        "results": [
            {"id": "101", "properties": {"firstname": "Alice"}},
            {"id": "102", "properties": {"firstname": "Bob"}}
        ],
        "paging": {
            "next": {
                "after": "cursor-2"
            }
        }
    }

    # Giả lập phản hồi trang 2: có 1 Contact
    page_2 = {
        "results": [
            {"id": "103", "properties": {"firstname": "Charlie"}}
        ]
    }

    response_1 = Mock()
    response_1.json.return_value = page_1

    response_2 = Mock()
    response_2.json.return_value = page_2

    # Giả lập requests.get trả về lần lượt 2 trang
    with patch(
    "src.sync_contacts.requests.request",
    side_effect=[response_1, response_2]
    ) as mock_request:

        contacts = list(
            get_hubspot_contacts("fake-test-token")
        )

    # Kiểm tra kết quả
    assert len(contacts) == 3
    assert mock_request.call_count == 2

    second_request_params = mock_request.call_args_list[1].kwargs["params"]

    assert second_request_params["after"] == "cursor-2"

    print("Pagination mock test passed!")
    print("Total contacts:", len(contacts))
    print("Total API calls:", mock_request.call_count)


if __name__ == "__main__":
    test_pagination()
