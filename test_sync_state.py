
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from src.sync_contacts import save_last_sync, load_last_sync


def test_sync_state():

    # Tạo file tạm để không ảnh hưởng state thật
    with tempfile.TemporaryDirectory() as temp_dir:

        test_state_file = Path(temp_dir) / "sync_state.json"

        with patch("src.sync_contacts.STATE_FILE", test_state_file):

            # Timestamp giả lập
            timestamp = 1795000000000

            # Lưu timestamp
            save_last_sync(timestamp)

            # Đọc lại timestamp
            loaded_timestamp = load_last_sync()

            # Kiểm tra dữ liệu
            assert loaded_timestamp == timestamp

            print("Sync state test passed!")
            print("Saved timestamp:", timestamp)
            print("Loaded timestamp:", loaded_timestamp)


if __name__ == "__main__":
    test_sync_state()

import tempfile
from pathlib import Path
from unittest.mock import patch

import src.sync_contacts as sync_module


def test_state_unchanged_after_sync_failure():

    old_timestamp = 1795000000000

    with tempfile.TemporaryDirectory() as temp_dir:

        temp_path = Path(temp_dir)

        # Tạo file service account giả để vượt qua bước kiểm tra file
        (temp_path / "service-account.json").touch()

        with patch.object(sync_module, "ROOT", temp_path), \
             patch.object(
                 sync_module, "STATE_FILE",
                 temp_path / "sync_state.json"
             ):

            # Lưu timestamp cũ
            sync_module.save_last_sync(old_timestamp)

            with patch.object(
                sync_module,
                "required_env",
                side_effect=[
                    "fake-token",
                    "fake-sheet-id",
                    "service-account.json"
                ]
            ), \
            patch.object(sync_module, "build_sheets_service"), \
            patch.object(sync_module, "ensure_header"), \
            patch.object(
                sync_module,
                "read_existing_contacts",
                return_value={}
            ), \
            patch.object(
                sync_module,
                "get_hubspot_contacts",
                side_effect=RuntimeError("Simulated API failure")
            ):

                try:
                    sync_module.sync()
                except RuntimeError:
                    pass
                else:
                    raise AssertionError("Expected sync to fail")

            # Đọc lại timestamp sau khi sync thất bại
            current_timestamp = sync_module.load_last_sync()

            assert current_timestamp == old_timestamp

            print("State failure test passed!")
            print("Old timestamp:", old_timestamp)
            print("Current timestamp:", current_timestamp)




def test_state_unchanged_after_sheets_failure():

    old_timestamp = 1795000000000

    with tempfile.TemporaryDirectory() as temp_dir:

        temp_path = Path(temp_dir)
        (temp_path / "service-account.json").touch()

        test_state_file = temp_path / "sync_state.json"

        fake_sheets = Mock()

        # Giả lập Google Sheets API lỗi khi append dữ liệu
        fake_sheets.spreadsheets.return_value.values.return_value.append.return_value.execute.side_effect = (
            RuntimeError("Simulated Google Sheets API failure")
        )

        with patch.object(sync_module, "ROOT", temp_path), \
             patch.object(sync_module, "STATE_FILE", test_state_file):

            sync_module.save_last_sync(old_timestamp)

            with patch.object(
                sync_module,
                "required_env",
                side_effect=[
                    "fake-token",
                    "fake-sheet-id",
                    "service-account.json"
                ]
            ), \
            patch.object(
                sync_module,
                "build_sheets_service",
                return_value=fake_sheets
            ), \
            patch.object(sync_module, "ensure_header"), \
            patch.object(
                sync_module,
                "read_existing_contacts",
                return_value={}
            ), \
            patch.object(
                sync_module,
                "get_hubspot_contacts",
                return_value=[
                    {
                        "id": "103",
                        "properties": {}
                    }
                ]
            ):

                try:
                    sync_module.sync()
                except RuntimeError as error:
                    assert "Google Sheets API failure" in str(error)
                else:
                    raise AssertionError("Expected sync to fail")

            current_timestamp = sync_module.load_last_sync()

            assert current_timestamp == old_timestamp

            print("Sheets failure test passed!")
            print("Old timestamp:", old_timestamp)
            print("Current timestamp:", current_timestamp)
if __name__ == "__main__":
    test_sync_state()
    test_state_unchanged_after_sync_failure()
    test_state_unchanged_after_sheets_failure()