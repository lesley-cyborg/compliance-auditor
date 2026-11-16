import os
from contextlib import closing

from db import get_connection, init_db


# Higher number = stronger encryption.
# This lets POLICY_MIN_BITLOCKER behave like a real minimum standard.
BITLOCKER_RANK = {
    "none": 0,
    "128-bit": 1,
    "256-bit": 2,
}


def evaluate_devices():
    """
    Evaluates all devices against the configured BitLocker policy.

    Policy:
    - POLICY_MIN_BITLOCKER=256-bit means only 256-bit is compliant.
    - POLICY_MIN_BITLOCKER=128-bit means 128-bit and 256-bit are compliant.
    - none is never compliant unless explicitly allowed, which we do not allow here.

    Returns summary metrics:
    {
        "total": int,
        "compliant": int,
        "non_compliant": int
    }
    """
    required_status = os.getenv("POLICY_MIN_BITLOCKER", "256-bit").strip()

    if required_status not in BITLOCKER_RANK:
        raise ValueError(
            f"Invalid POLICY_MIN_BITLOCKER: '{required_status}'. "
            f"Valid values are: {', '.join(BITLOCKER_RANK.keys())}"
        )

    required_rank = BITLOCKER_RANK[required_status]

    # Safe to call repeatedly because schema uses CREATE TABLE IF NOT EXISTS.
    init_db()

    print(f"🔎 Evaluating devices against minimum policy: {required_status}")

    with closing(get_connection()) as conn:
        with conn:
            rows = conn.execute(
                """
                SELECT device_id, bitlocker_status
                FROM devices
                """
            ).fetchall()

            updates = []
            compliant_count = 0

            for row in rows:
                device_id = row["device_id"]
                current_status = row["bitlocker_status"]

                current_rank = BITLOCKER_RANK.get(current_status, -1)
                is_compliant = int(current_rank >= required_rank)

                if is_compliant:
                    compliant_count += 1

                updates.append((is_compliant, device_id))

            conn.executemany(
                """
                UPDATE devices
                SET is_compliant = ?
                WHERE device_id = ?
                """,
                updates,
            )

    total = len(rows)
    non_compliant = total - compliant_count

    summary = {
        "total": total,
        "compliant": compliant_count,
        "non_compliant": non_compliant,
    }

    print(
        f"✅ Evaluation complete. "
        f"Total: {total} | Compliant: {compliant_count} | Non-compliant: {non_compliant}"
    )

    return summary


if __name__ == "__main__":
    try:
        evaluate_devices()
    except Exception as exc:
        print(f"❌ Evaluation failed: {exc}")
        raise SystemExit(1)