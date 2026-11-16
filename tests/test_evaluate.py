from contextlib import closing

import pytest

import db
from evaluate import evaluate_devices


def setup_test_db(tmp_path, monkeypatch):
    """
    Uses a temporary SQLite database for each test.
    This avoids touching the real data/compliance.db file.
    """
    test_db_path = tmp_path / "test_compliance.db"
    monkeypatch.setattr(db, "DB_PATH", str(test_db_path))
    db.init_db()


def insert_device(device_id, hostname, bitlocker_status):
    with closing(db.get_connection()) as conn:
        with conn:
            conn.execute(
                """
                INSERT INTO devices (
                    device_id,
                    hostname,
                    bitlocker_status,
                    last_seen,
                    is_compliant
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    device_id,
                    hostname,
                    bitlocker_status,
                    "2026-11-17T10:00:00",
                    0,
                ),
            )


def get_compliance_map():
    with closing(db.get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT device_id, is_compliant
            FROM devices
            """
        ).fetchall()

    return {row["device_id"]: row["is_compliant"] for row in rows}


def test_evaluate_with_256_bit_policy(tmp_path, monkeypatch):
    setup_test_db(tmp_path, monkeypatch)
    monkeypatch.setenv("POLICY_MIN_BITLOCKER", "256-bit")

    insert_device("DEV001", "WORKSTATION-A", "256-bit")
    insert_device("DEV002", "WORKSTATION-B", "128-bit")
    insert_device("DEV003", "WORKSTATION-C", "none")

    summary = evaluate_devices()

    assert summary == {
        "total": 3,
        "compliant": 1,
        "non_compliant": 2,
    }

    compliance = get_compliance_map()

    assert compliance["DEV001"] == 1
    assert compliance["DEV002"] == 0
    assert compliance["DEV003"] == 0


def test_evaluate_with_128_bit_policy(tmp_path, monkeypatch):
    setup_test_db(tmp_path, monkeypatch)
    monkeypatch.setenv("POLICY_MIN_BITLOCKER", "128-bit")

    insert_device("DEV001", "WORKSTATION-A", "256-bit")
    insert_device("DEV002", "WORKSTATION-B", "128-bit")
    insert_device("DEV003", "WORKSTATION-C", "none")

    summary = evaluate_devices()

    assert summary == {
        "total": 3,
        "compliant": 2,
        "non_compliant": 1,
    }

    compliance = get_compliance_map()

    assert compliance["DEV001"] == 1
    assert compliance["DEV002"] == 1
    assert compliance["DEV003"] == 0


def test_evaluate_with_invalid_policy(tmp_path, monkeypatch):
    setup_test_db(tmp_path, monkeypatch)
    monkeypatch.setenv("POLICY_MIN_BITLOCKER", "512-bit")

    with pytest.raises(ValueError, match="Invalid POLICY_MIN_BITLOCKER"):
        evaluate_devices()


def test_evaluate_with_no_devices(tmp_path, monkeypatch):
    setup_test_db(tmp_path, monkeypatch)
    monkeypatch.setenv("POLICY_MIN_BITLOCKER", "256-bit")

    summary = evaluate_devices()

    assert summary == {
        "total": 0,
        "compliant": 0,
        "non_compliant": 0,
    }
    