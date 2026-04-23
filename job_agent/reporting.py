from __future__ import annotations

import csv
import json
from pathlib import Path

from job_agent.ranking import RankedJob


def _job_to_dict(item: RankedJob) -> dict[str, object]:
    job = item.listing
    return {
        "score": item.score,
        "is_new": item.is_new,
        "source": job.source,
        "company": job.company,
        "title": job.title,
        "location": job.location,
        "remote": job.remote,
        "employment_type": job.employment_type,
        "salary": job.salary,
        "url": job.url,
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        "reasons": item.reasons,
    }


def write_reports(output_dir: Path, ranked_jobs: list[RankedJob], warnings: list[str]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "top_matches.json"
    csv_path = output_dir / "top_matches.csv"
    md_path = output_dir / "top_matches.md"
    new_md_path = output_dir / "new_matches.md"

    payload = {
        "count": len(ranked_jobs),
        "warnings": warnings,
        "jobs": [_job_to_dict(item) for item in ranked_jobs],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "score",
                "is_new",
                "source",
                "company",
                "title",
                "location",
                "remote",
                "employment_type",
                "salary",
                "posted_at",
                "url",
                "reasons",
            ],
        )
        writer.writeheader()
        for item in ranked_jobs:
            row = _job_to_dict(item)
            row["reasons"] = " | ".join(item.reasons)
            writer.writerow(row)

    md_lines = ["# Top Matches", ""]
    if warnings:
        md_lines.extend(["## Warnings", ""])
        md_lines.extend([f"- {warning}" for warning in warnings])
        md_lines.append("")

    for index, item in enumerate(ranked_jobs, start=1):
        job = item.listing
        md_lines.append(f"## {index}. {job.title} - {job.company}")
        md_lines.append("")
        md_lines.append(f"- Score: `{item.score}`")
        md_lines.append(f"- Source: `{job.source}`")
        md_lines.append(f"- Location: `{job.location or 'Unknown'}`")
        md_lines.append(f"- Remote: `{'yes' if job.remote else 'no'}`")
        if job.posted_at:
            md_lines.append(f"- Posted: `{job.posted_at.date().isoformat()}`")
        if job.salary:
            md_lines.append(f"- Salary: `{job.salary}`")
        md_lines.append(f"- Reasons: {'; '.join(item.reasons) if item.reasons else 'general resume fit'}")
        md_lines.append(f"- Link: {job.url}")
        md_lines.append("")

    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    new_lines = ["# New Matches", ""]
    new_jobs = [item for item in ranked_jobs if item.is_new]
    if not new_jobs:
        new_lines.append("No newly discovered matches in this run.")
    else:
        for index, item in enumerate(new_jobs, start=1):
            job = item.listing
            new_lines.append(f"{index}. [{job.title} - {job.company}]({job.url})")
            new_lines.append(f"   Score: {item.score} | Location: {job.location or 'Unknown'}")
            new_lines.append(f"   Reasons: {'; '.join(item.reasons) if item.reasons else 'general resume fit'}")
            new_lines.append("")
    new_md_path.write_text("\n".join(new_lines), encoding="utf-8")
