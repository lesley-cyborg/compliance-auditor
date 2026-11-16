# 🛡️ Automated Endpoint Compliance Auditor

A resilient, local CLI tool that automates endpoint security compliance checks. It ingests device inventory, evaluates it against a configurable security policy (e.g., BitLocker encryption standards), persists the state, and alerts on violations via Discord.

Built with a "boring by default" philosophy: prioritizing reliability, simplicity, and zero-infrastructure overhead over cloud-native complexity.

## 🏗️ Architecture & Flow

```text
[ mock_inventory.csv ] ──(ingest.py)──▶ [ SQLite Database ]
                                              │
                                              ▼
                                       (evaluate.py)
                                              │
                                              ▼
[ Discord Webhook ] ◀──(alert.py)─── [ Non-Compliant Devices ]
       │                                      │
       └──(on 429/500 error)──▶ [ failed_alerts.json (Dead Letter Queue) ]

## 🚀 Quick Start

## Prerequisites

Python 3.10+
A free Discord Server with an Incoming Webhook configured.

##Installation

git clone https://github.com/yourusername/compliance-auditor.git
cd compliance-auditor
python -m venv venv

# Activate virtual environment
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

pip install -r requirements.txt

## Configuration

Copy the example environment file and add your Discord Webhook URL:

cp .env.example .env
# Edit .env and add your DISCORD_WEBHOOK_URL

## Usage

The tool uses argparse subcommands. You can run the pipeline step-by-step, or all at once.

# Run the entire pipeline (Ingest -> Evaluate -> Alert)
python main.py run --file mock_inventory.csv

# Or run steps individually:
python main.py ingest --file mock_inventory.csv
python main.py evaluate
python main.py alert

## 🛡️ Resiliency & Failure Handling

This tool is designed to handle the messy reality of enterprise data and network flakiness.
Data Quality Failures: If the input CSV contains malformed rows (e.g., missing device_id or invalid encryption status), the ingest process catches the error, logs the raw row and exception to data/audit.log, and continues processing. It never crashes the whole run.
Network/Alerting Failures: If the Discord webhook returns a 429 Too Many Requests or 500 Server Error, the alert process uses the tenacity library to automatically retry with exponential backoff (up to 3 attempts).
Dead Letter Queue (DLQ): If the webhook fails permanently after all retries, the alert payload is safely wrapped with a timestamp and written to data/failed_alerts.json for manual review, ensuring no compliance violations are silently dropped.

## 🧠 Design Decisions & ADRs

ADR 001: Database Selection (SQLite over PostgreSQL)
Context: Needed a persistent datastore for device state.
Decision: Use Python's built-in sqlite3 module.
Consequences: Zero infrastructure overhead, zero credentials to manage, and instant local execution. Postgres was rejected as it violates the "boring by default" principle for a local CLI tool processing <10,000 records.

ADR 002: Database Indexing Strategy (Partial Index)
Context: Needed to optimize the query that fetches non-compliant devices for alerting.
Decision: Implemented a Partial Index: CREATE INDEX idx_non_compliant ON devices(device_id) WHERE is_compliant = 0;
Consequences: In a healthy environment, 95%+ of devices are compliant. A standard B-Tree index on a boolean column is highly inefficient and usually ignored by the query planner. A partial index keeps the index footprint tiny and ensures O(log N) lookups specifically for the 5% of devices we actually care about.

ADR 003: Alerting Mechanism
Context: Needed automated alerting without setting up SMTP servers or paid SaaS.
Decision: Discord Incoming Webhooks with Rich Embeds.
Consequences: Zero cost, instant visual feedback, and easy to screenshot for portfolio/documentation purposes.

## 🧪 Testing

The project includes a comprehensive pytest suite (11 tests) covering happy paths and failure modes, using temporary databases to ensure complete isolation.

Tests include mocking malformed CSVs to verify audit.log behavior, asserting idempotency (no duplicate rows on re-run), and mocking HTTP 429/500 responses to verify tenacity retry logic and failed_alerts.json fallback.

## 🔄 Future Improvements (Scaling to 10x)
If this tool were promoted to a production enterprise service processing >10,000 devices concurrently, the following changes would be triggered:

Database Migration: Migrate from SQLite to PostgreSQL to handle concurrent write locks and larger dataset footprints.

Transactional Outbox Pattern: Currently, failed alerts are written to a local JSON file. In a distributed system, this risks data loss. I would implement the Outbox Pattern by writing failed alerts to a pending_alerts table in the database within the same transaction as the compliance evaluation, ensuring at-least-once delivery via a separate background worker.

Authentication: Add API key validation or OAuth2 if exposing this logic via a REST API.



