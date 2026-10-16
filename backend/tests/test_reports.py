from unittest.mock import Mock

from kombu.exceptions import OperationalError
from redis.exceptions import ConnectionError

from app import main


def test_report_request_is_async(client, monkeypatch):
    enqueue = Mock(return_value=Mock(id="task-123"))
    monkeypatch.setattr(main.refresh_report, "delay", enqueue)
    response = client.post("/api/reports")
    assert response.status_code == 202
    assert response.json() == {"task_id": "task-123", "status": "queued"}
    enqueue.assert_called_once_with()


def test_broker_failure_does_not_break_catalog(client, monkeypatch):
    monkeypatch.setattr(main.refresh_report, "delay", Mock(side_effect=OperationalError("offline")))
    assert client.post("/api/reports").status_code == 503
    assert client.get("/api/products").status_code == 200


def test_report_cache_outage_is_explicit(client, monkeypatch):
    monkeypatch.setattr(main, "redis_client", Mock(side_effect=ConnectionError("offline")))
    assert client.get("/api/reports/latest").status_code == 503
