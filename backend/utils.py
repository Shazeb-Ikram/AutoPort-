# backend/utils.py
"""
Logging and lightweight metadata DB utilities for AutoPort (Phase G).
Provides:
 - setup_logging(): root console + app.log rotating handler
 - get_logger(name): returns a module-specific logger that writes to logs/<shortname>.log
 - init_metadata_db(), log_report_metadata(), list_reports()
"""
import logging
from logging.handlers import RotatingFileHandler
import os
import sqlite3
import json
from datetime import datetime
from typing import Iterable

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
DEFAULT_DB = os.path.join(BASE_DIR, 'metadata.db')

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def setup_logging(log_dir: str = None,
                  console_level=logging.INFO,
                  file_level=logging.INFO,
                  max_bytes: int = 5 * 1024 * 1024,
                  backup_count: int = 5):
    """
    Configure root logger once. Creates logs/app.log and console handler.
    Call early in entrypoint scripts (run_demo.py, run_scheduler.py).
    """
    log_dir = log_dir or LOG_DIR
    ensure_dir(log_dir)

    root_logger = logging.getLogger()
    # avoid re-configuring when called multiple times
    if getattr(root_logger, "_autoport_configured", False):
        return
    root_logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(console_level)
    ch.setFormatter(fmt)
    root_logger.addHandler(ch)

    # Rotating file for general app-level messages
    app_log = os.path.join(log_dir, 'app.log')
    fh = RotatingFileHandler(app_log, maxBytes=max_bytes, backupCount=backup_count)
    fh.setLevel(file_level)
    fh.setFormatter(fmt)
    root_logger.addHandler(fh)

    root_logger._autoport_configured = True

def get_logger(name: str, log_dir: str = None,
               file_level=logging.INFO,
               max_bytes: int = 5 * 1024 * 1024,
               backup_count: int = 5):
    """
    Return a logger which writes to logs/<shortname>.log and also propagates to root.
    Example: logger = get_logger(__name__)
    """
    log_dir = log_dir or LOG_DIR
    ensure_dir(log_dir)
    short = name.split('.')[-1]
    logger = logging.getLogger(name)

    # avoid adding duplicate handlers
    if getattr(logger, "_autoport_configured", False):
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')

    file_path = os.path.join(log_dir, f'{short}.log')
    fh = RotatingFileHandler(file_path, maxBytes=max_bytes, backupCount=backup_count)
    fh.setLevel(file_level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Let messages also propagate to root (console + app.log)
    logger.propagate = True
    logger._autoport_configured = True
    return logger

# -------------------------
# Simple metadata DB helpers (optional, recommended)
# -------------------------
def init_metadata_db(db_path: str = None):
    db_path = db_path or DEFAULT_DB
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS reports (
      id INTEGER PRIMARY KEY,
      name TEXT,
      timestamp TEXT,
      source_files TEXT,
      status TEXT,
      details TEXT
    )
    ''')
    conn.commit()
    conn.close()
    return db_path

def log_report_metadata(name: str, source_files: Iterable[str], status: str = 'success', details: str = None, db_path: str = None):
    db_path = db_path or init_metadata_db()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    ts = datetime.utcnow().isoformat() + 'Z'
    c.execute('INSERT INTO reports (name, timestamp, source_files, status, details) VALUES (?,?,?,?,?)',
              (name, ts, json.dumps(list(source_files)), status, details or ""))
    conn.commit()
    conn.close()
    return True

def list_reports(limit: int = 20, db_path: str = None):
    db_path = db_path or DEFAULT_DB
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT id, name, timestamp, status FROM reports ORDER BY id DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows
