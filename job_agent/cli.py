from __future__ import annotations

import argparse
from pathlib import Path

from job_agent.runner import run_job_search


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resume-aware job search bot — scores and ranks listings against your resume.")
    parser.add_argument("--resume", required=True, type=Path, help="Path to the resume file (pdf, docx, txt, md).")
    parser.add_argument("--search-config", type=Path, default=Path("config/search.yaml"))
    parser.add_argument("--company-config", type=Path, default=Path("config/company_boards.yaml"))
    parser.add_argument("--limit", type=int, default=None, help="Override the configured report limit.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = run_job_search(
        resume_path=args.resume,
        search_config_path=args.search_config,
        company_config_path=args.company_config,
        limit=args.limit,
    )

    print(f"Processed {result.raw_job_count} raw jobs.")
    print(f"Wrote {len(result.ranked_jobs)} ranked matches to {result.app_config.runtime.output_dir}.")
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
