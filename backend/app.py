"""RDAS proof-of-concept incident ingestion API. Not an emergency dispatch service."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parents[1]
DB = Path(os.getenv('RDAS_DB', str(BASE / 'incidents.db')))
app = FastAPI(title='RDAS Prototype API', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:8000', 'http://127.0.0.1:8000'], allow_methods=['GET','POST'], allow_headers=['*'])

@contextmanager
def database():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS incidents (
            id TEXT PRIMARY KEY, device_id TEXT NOT NULL,
            latitude REAL NOT NULL, longitude REAL NOT NULL,
            score REAL NOT NULL, captured_at TEXT NOT NULL, received_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'unverified')''')
        conn.commit()
        yield conn
    finally:
        conn.close()

class Incident(BaseModel):
    id: str = Field(min_length=5, max_length=100)
    device_id: str = Field(min_length=1, max_length=100)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    score: float = Field(ge=0, le=1)
    captured_at: datetime

@app.get('/')
def dashboard():
    return FileResponse(BASE / 'dashboard' / 'index.html')

@app.get('/health')
def health():
    return {'status': 'ok', 'prototype': True}

@app.post('/incidents', status_code=201)
def ingest(incident: Incident):
    with database() as conn:
        exists = conn.execute('SELECT id FROM incidents WHERE id=?', (incident.id,)).fetchone()
        if exists:
            return {'id': incident.id, 'status': 'already_received'}
        conn.execute('''INSERT INTO incidents
            (id,device_id,latitude,longitude,score,captured_at,received_at)
            VALUES (?,?,?,?,?,?,?)''', (
            incident.id, incident.device_id, incident.latitude, incident.longitude,
            incident.score, incident.captured_at.isoformat(),
            datetime.now(timezone.utc).isoformat()))
        conn.commit()
    return {'id': incident.id, 'status': 'stored_unverified'}

@app.get('/incidents')
def list_incidents():
    with database() as conn:
        rows = conn.execute('SELECT * FROM incidents ORDER BY received_at DESC LIMIT 100').fetchall()
        return [dict(row) for row in rows]
