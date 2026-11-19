from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend import app as api

def test_ingest_deduplicates(tmp_path, monkeypatch):
    monkeypatch.setattr(api, 'DB', tmp_path / 'test.db')
    client = TestClient(api.app)
    event = {'id':'sample-unique-123','device_id':'test-pi', 'latitude':-1.9441,
             'longitude':30.0619,'score':0.87,'captured_at':datetime.now(timezone.utc).isoformat()}
    first = client.post('/incidents', json=event)
    assert first.status_code == 201
    second = client.post('/incidents', json=event)
    assert second.json()['status'] == 'already_received'
    assert len(client.get('/incidents').json()) == 1
