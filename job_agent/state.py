from __future__ import annotations

import sqlite3
from pathlib import Path

from job_agent.ranking import RankedJob


SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_jobs (
  rank_key TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  company TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_score REAL NOT NULL
);
"""


def mark_seen_jobs(sqlite_path: Path, ranked_jobs: list[RankedJob]) -> list[RankedJob]:
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(sqlite_path)
    try:
        connection.execute(SCHEMA)
        for item in ranked_jobs:
            row = connection.execute(
                "SELECT rank_key FROM seen_jobs WHERE rank_key = ?",
                (item.rank_key,),
            ).fetchone()
            item.is_new = row is None
            if row is None:
                connection.execute(
                    """
                    INSERT INTO seen_jobs (rank_key, source, company, title, url, last_score)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.rank_key,
                        item.listing.source,
                        item.listing.company,
                        item.listing.title,
                        item.listing.url,
                        item.score,
                    ),
                )
            else:
                connection.execute(
                    """
                    UPDATE seen_jobs
                    SET last_seen_at = CURRENT_TIMESTAMP, last_score = ?
                    WHERE rank_key = ?
                    """,
                    (item.score, item.rank_key),
                )
        connection.commit()
    finally:
        connection.close()
    return ranked_jobs
