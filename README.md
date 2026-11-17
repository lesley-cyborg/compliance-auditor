# 🛡️ Automated Endpoint Compliance Auditor (V2: Distributed Service)

A resilient, distributed REST API for automated endpoint security compliance checks. It ingests device inventory, evaluates it against configurable security policies, and guarantees alert delivery using the **Transactional Outbox Pattern**.

Built with a "boring by default" philosophy, prioritizing data integrity, API security, and decoupled background processing over unnecessary cloud complexity.

## 🏗️ Architecture & Flow

```text
[ Client / CI/CD ] ──(HTTP POST + API Key)──▶ [ FastAPI Server ]
                                                    │
                                                    ▼ (1. Upsert)
                                            [ PostgreSQL Database ]
                                                    │
                                                    ▼ (2. Evaluate & Queue)
                                            [ Outbox Table (JSONB) ] 
                                                    │
                                                    ▼ (3. Poll every 30s)
[ Discord Webhook ] ◀──(Tenacity Retries)── [ Background Worker (worker.py) ]# 🛡️ Automated Endpoint Compliance Auditor (V2: Distributed Service)

A resilient, distributed REST API for automated endpoint security compliance checks. It ingests device inventory, evaluates it against configurable security policies, and guarantees alert delivery using the **Transactional Outbox Pattern**.

Built with a "boring by default" philosophy, prioritizing data integrity, API security, and decoupled background processing over unnecessary cloud complexity.

## 🏗️ Architecture & Flow

```text
[ Client / CI/CD ] ──(HTTP POST + API Key)──▶ [ FastAPI Server ]
                                                    │
                                                    ▼ (1. Upsert)
                                            [ PostgreSQL Database ]
                                                    │
                                                    ▼ (2. Evaluate & Queue)
                                            [ Outbox Table (JSONB) ] 
                                                    │
                                                    ▼ (3. Poll every 30s)
[ Discord Webhook ] ◀──(Tenacity Retries)── [ Background Worker (worker.py) ]

## 🚀 Quick Start

## Prerequisites

Python 3.10+
PostgreSQL 15+ installed locally (or via Docker)
A free Discord Server with an Incoming Webhook configured.

##Installation

git clone https://github.com/yourusername/compliance-auditor.git
cd compliance-auditor
git checkout v2-distributed-service #Ensure you are on the V2 branch
python -m venv venv

# Activate virtual environment
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

pip install -r requirements.txt

## Configuration

Copy the example environment file and add your Discord Webhook URL:

cp .env.example .env
# Edit .env and add your DISCORD_WEBHOOK_URL

## Running the Service

You will need two terminal windows: one for the API, one for the background worker.

Terminal 1: Start the FastAPI Server 

uvicorn main:app --reload
# API will be available at http://127.0.0.1:8000
# Interactive Swagger UI: http://127.0.0.1:8000/docs

Terminal 2: Start the Background Worker

python worker.py
# Will poll the outbox table every 30 seconds

Using the API

All protected endpoints require the X-API-Key header.

Go to http://127.0.0.1:8000/docs
Click Authorize at the top right.
Enter your API key (default: super-secret-api-key-123).
Use the UI to POST /ingest (upload a CSV), POST /evaluate, and watch the worker automatically trigger POST /alert.

🧠 Design Decisions & ADRs

ADR 001: Database Selection (PostgreSQL over SQLite)

Context: V1 used SQLite. V2 targets a distributed service architecture where multiple processes (API server + background worker) need concurrent, safe access to the same data.

Decision: Migrate to PostgreSQL.

Consequences: Eliminates SQLite file-locking issues during concurrent reads/writes. Enables advanced features like native JSONB for the Outbox pattern.

ADR 002: The Transactional Outbox Pattern

Context: In V1, failed alerts were written to a local JSON file. In a distributed system, updating the database and sending an HTTP request are two separate operations, risking data loss if the server crashes between them.

Decision: Implement the Outbox Pattern. When evaluate runs, it updates the devices table AND inserts a record into the outbox table in the same database transaction.

Consequences: Guarantees at-least-once delivery. The background worker safely polls the outbox table. If Discord is down, the record remains processed = FALSE and is retried on the next cycle.

ADR 003: API Authentication

Context: Exposing compliance data and alerting mechanisms requires basic access control without the overhead of full OAuth2 for an internal tool.

Decision: API Key authentication via a custom X-API-Key header, enforced via FastAPI dependencies.

Consequences: Lightweight, stateless, and easy to rotate. Requests without the key are rejected with 403 Forbidden before hitting business logic.

🔄 Future Improvements (Scaling to 100x)

If this service scales to process >100,000 devices or requires high availability:

Message Queue: Replace the polling worker.py with an event-driven architecture using RabbitMQ or AWS SQS, triggered by Postgres logical replication (e.g., Debezium).

Containerization: Package the API and Worker into separate Docker containers and deploy via Kubernetes or AWS ECS.

Observability: Integrate Prometheus/Grafana for metrics (e.g., outbox_queue_depth, alert_success_rate) and OpenTelemetry for distributed tracing.
