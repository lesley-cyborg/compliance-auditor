import os
import pytest
import db
from ingest import ingest_csv

def setup_test_db(tmp_path, monkeypatch):
    """Points the database to a temporary file for isolated testing."""
    test_db_path = tmp_path / "test_compliance.db"
    monkeypatch.setattr(db, "DB_PATH", str(test_db_path))
    db.init_db()

def get_device_count():
    """Helper to count rows in the current test database."""
    with db.get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]

def test_ingest_happy_path_and_idempotency(tmp_path, monkeypatch):
    """Tests that valid data is ingested and running it twice doesn't create duplicates."""
    setup_test_db(tmp_path, monkeypatch)
    
    # Create a temporary valid CSV
    csv_path = tmp_path / "valid.csv"
    csv_path.write_text(
        "device_id,hostname,bitlocker_status,last_seen\n"
        "DEV001,PC-A,256-bit,2026-11-17T10:00:00\n"
        "DEV002,PC-B,128-bit,2026-11-17T10:00:00\n"
    )
    
    # First run
    processed, skipped = ingest_csv(str(csv_path))
    assert processed == 2
    assert skipped == 0
    assert get_device_count() == 2
    
    # Second run (Idempotency check: should overwrite, not duplicate)
    processed, skipped = ingest_csv(str(csv_path))
    assert processed == 2
    assert skipped == 0
    assert get_device_count() == 2  # Still 2, not 4!

def test_ingest_skips_missing_device_id(tmp_path, monkeypatch):
    """Tests that rows with missing device_id are skipped and logged."""
    setup_test_db(tmp_path, monkeypatch)
    
    csv_path = tmp_path / "missing_id.csv"
    csv_path.write_text(
        "device_id,hostname,bitlocker_status,last_seen\n"
        "DEV001,PC-A,256-bit,2026-11-17T10:00:00\n"
        ",PC-B-NO-ID,128-bit,2026-11-17T10:00:00\n"  # Empty device_id
    )
    
    processed, skipped = ingest_csv(str(csv_path))
    
    assert processed == 1
    assert skipped == 1
    assert get_device_count() == 1
    
    # Verify the correct device made it in
    with db.get_connection() as conn:
        row = conn.execute("SELECT device_id FROM devices").fetchone()
        assert row["device_id"] == "DEV001"

def test_ingest_skips_invalid_bitlocker_status(tmp_path, monkeypatch):
    """Tests that invalid enum values are caught and skipped."""
    setup_test_db(tmp_path, monkeypatch)
    
    csv_path = tmp_path / "invalid_status.csv"
    csv_path.write_text(
        "device_id,hostname,bitlocker_status,last_seen\n"
        "DEV001,PC-A,512-bit,2026-11-17T10:00:00\n"  # Invalid status
    )
    
    processed, skipped = ingest_csv(str(csv_path))
    
    assert processed == 0
    assert skipped == 1
    assert get_device_count() == 0

def test_ingest_missing_file(tmp_path, monkeypatch):
    """Tests graceful handling of a non-existent file."""
    setup_test_db(tmp_path, monkeypatch)
    
    # Should return None and not crash
    result = ingest_csv("this_file_does_not_exist.csv")
    assert result is None
    assert get_device_count() == 0

def test_ingest_missing_columns(tmp_path, monkeypatch):
    """Tests that a CSV with wrong headers is rejected entirely."""
    setup_test_db(tmp_path, monkeypatch)
    
    csv_path = tmp_path / "wrong_headers.csv"
    csv_path.write_text(
        "id,name,status\n"  # Missing required columns
        "DEV001,PC-A,256-bit\n"
    )
    
    # Should return None and not crash
    result = ingest_csv(str(csv_path))
    assert result is None
    assert get_device_count() == 0