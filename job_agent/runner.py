from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from job_agent.config import AppConfig, load_app_config
from job_agent.ranking import RankedJob, filter_and_rank_jobs
from job_agent.reporting import write_reports
from job_agent.resume import ResumeProfile, load_resume_profile
from job_agent.sources import fetch_all_jobs
from job_agent.state import mark_seen_jobs


@dataclass
class JobRunResult:
    app_config: AppConfig
    resume: ResumeProfile
    raw_job_count: int
    ranked_jobs: list[RankedJob]
    warnings: list[str]


def run_job_search(
    resume_path: Path,
    search_config_path: Path,
    company_config_path: Path,
    limit: int | None = None,
) -> JobRunResult:
    app_config = load_app_config(search_config_path, company_config_path)
    resume = load_resume_profile(resume_path)
    jobs, warnings = fetch_all_jobs(app_config)
    final_limit = limit or app_config.preferences.report_limit
    ranked_jobs = filter_and_rank_jobs(jobs, resume, app_config.preferences, final_limit)
    ranked_jobs = mark_seen_jobs(app_config.runtime.sqlite_path, ranked_jobs)
    write_reports(app_config.runtime.output_dir, ranked_jobs, warnings)
    return JobRunResult(
        app_config=app_config,
        resume=resume,
        raw_job_count=len(jobs),
        ranked_jobs=ranked_jobs,
        warnings=warnings,
    )
