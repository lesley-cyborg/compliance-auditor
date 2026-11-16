import json
import os
import pytest
import requests
from unittest.mock import patch, MagicMock

import db
import alert

def setup_test_db(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test_compliance.db"
    monkeypatch.setattr(db, "DB_PATH", str(test_db_path))
    db.init_db()

def insert_device(device_id, hostname, bitlocker_status, is_compliant):
    with db.get_connection() as conn:
        conn.execute(
            "INSERT INTO devices (device_id, hostname, bitlocker_status, last_seen, is_compliant) VALUES (?, ?, ?, ?, ?)",
            (device_id, hostname, bitlocker_status, "2026-11-17T10:00:00", is_compliant)
        )

def test_alert_happy_path(tmp_path, monkeypatch):
    setup_test_db(tmp_path, monkeypatch)
    insert_device("DEV001", "BAD-PC", "128-bit", 0)
    
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://fake-webhook.com")
    
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    
    with patch("alert.requests.post", return_value=mock_response) as mock_post:
        alert.alert()
        mock_post.assert_called_once()

def test_alert_dead_letter_queue(tmp_path, monkeypatch):
    setup_test_db(tmp_path, monkeypatch)
    insert_device("DEV002", "BAD-PC-2", "none", 0)
    
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://fake-webhook.com")
    
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
    
    with patch("alert.requests.post", return_value=mock_response):
        original_dir = os.getcwd()
        # Point the fallback path to the temp directory for this test
        monkeypatch.setattr(alert, "FAILED_ALERTS_PATH", str(tmp_path / "failed_alerts.json"))
        
        try:
            alert.alert()
            
            fallback_file = tmp_path / "failed_alerts.json"
            assert fallback_file.exists()
            
            with open(fallback_file, 'r') as f:
                saved_data = json.load(f)
            
            assert len(saved_data) == 1
            # Verify it has the metadata wrapper
            assert "failed_at" in saved_data[0]
            assert "payload" in saved_data[0]
            assert "BAD-PC-2" in saved_data[0]["payload"]["embeds"][0]["description"]
        finally:
            os.chdir(original_dir)