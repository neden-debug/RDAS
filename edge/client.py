"""Offline-first event queue and retrying uploader. Run `python -m edge.client`."""
import argparse
import json
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import requests
from edge.detector import CandidateDetector

DB = Path(os.getenv('RDAS_QUEUE_DB', 'edge_queue.db'))
API = os.getenv('RDAS_API', 'http://127.0.0.1:8000')

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.execute('CREATE TABLE IF NOT EXISTS queue (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    conn.commit()
    return conn

def enqueue(conn, data):
    conn.execute('INSERT OR IGNORE INTO queue VALUES (?,?)', (data['id'], json.dumps(data)))
    conn.commit()

def sync(conn, api=API):
    """Failed items remain durable; duplicates are safe on retry."""
    count = 0
    for event_id, payload in conn.execute('SELECT id, payload FROM queue ORDER BY rowid').fetchall():
        try:
            response = requests.post(f'{api}/incidents', json=json.loads(payload), timeout=5)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f'Connection unavailable; {event_id} remains queued: {exc}')
            break
        conn.execute('DELETE FROM queue WHERE id=?', (event_id,))
        conn.commit()
        count += 1
    return count

def simulate(conn):
    """Synthetic readings only; GPS point is sample coordinates, not a live device."""
    detector = CandidateDetector()
    examples = [(0.12, 0.95, 0.2)] * 10 + [(0.95, 0.85, 0.9)] * 10
    found = 0
    for vision, impact, drop in examples:
        if detector.update(vision, impact, drop):
            event = dict(id=str(uuid.uuid4()), device_id='demo-pi-001',
                         latitude=-1.9441, longitude=30.0619, score=0.89,
                         captured_at=datetime.now(timezone.utc).isoformat())
            enqueue(conn, event)
            found += 1
    print(f'Synthetic accident candidates queued: {found} (pothole samples should not trigger)')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--simulate', action='store_true', help='Generate synthetic samples')
    parser.add_argument('--sync', action='store_true', help='Send durable events to API')
    parser.add_argument('--watch', action='store_true', help='Retry every 10-60 sec until stopped')
    args = parser.parse_args()
    with connect() as conn:
        if args.simulate:
            simulate(conn)
        if args.sync:
            print('Events sent:', sync(conn))
        if args.watch:
            backoff = 10
            try:
                while True:
                    sent = sync(conn)
                    backoff = 10 if sent else min(backoff * 2, 60)
                    time.sleep(backoff)
            except KeyboardInterrupt:
                pass
        if not (args.simulate or args.sync or args.watch):
            parser.print_help()
