from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SearchPreferences:
    target_titles: list[str] = field(default_factory=list)
    boost_keywords: list[str] = field(default_factory=list)
    avoid_keywords: list[str] = field(default_factory=list)
    preferred_industries: list[str] = field(default_factory=list)
    preferred_seniority_terms: list[str] = field(default_factory=list)
    minimum_keyword_matches: int = 1
    minimum_industry_matches: int = 0
    require_title_or_keyword_match: bool = False
    require_industry_match: bool = False
    require_seniority_match: bool = False
    remote_only_or_phoenix: bool = True
    prefer_remote: bool = True
    prefer_phoenix: bool = True
    usa_only_remote: bool = True
    phoenix_metro_terms: list[str] = field(
        default_factory=lambda: [
            "phoenix",
            "scottsdale",
            "tempe",
            "mesa",
            "chandler",
            "gilbert",
            "glendale",
            "peoria",
        ]
    )
    report_limit: int = 100


@dataclass
class RuntimeConfig:
    output_dir: Path
    sqlite_path: Path
    request_timeout_seconds: int = 25
    user_agent: str = "JobAgent/0.1"


@dataclass
class CompanyBoard:
    provider: str
    slug: str
    label: str = ""


@dataclass
class AppConfig:
    preferences: SearchPreferences
    runtime: RuntimeConfig
    companies: list[CompanyBoard]


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return raw


def load_search_config(path: Path) -> tuple[SearchPreferences, RuntimeConfig]:
    data = _read_yaml(path)
    preferences_raw = data.get("preferences", {})
    runtime_raw = data.get("runtime", {})

    preferences = SearchPreferences(
        target_titles=[str(item).strip().lower() for item in preferences_raw.get("target_titles", []) if str(item).strip()],
        boost_keywords=[str(item).strip().lower() for item in preferences_raw.get("boost_keywords", []) if str(item).strip()],
        avoid_keywords=[str(item).strip().lower() for item in preferences_raw.get("avoid_keywords", []) if str(item).strip()],
        preferred_industries=[str(item).strip().lower() for item in preferences_raw.get("preferred_industries", []) if str(item).strip()],
        preferred_seniority_terms=[str(item).strip().lower() for item in preferences_raw.get("preferred_seniority_terms", []) if str(item).strip()],
        minimum_keyword_matches=int(preferences_raw.get("minimum_keyword_matches", 1)),
        minimum_industry_matches=int(preferences_raw.get("minimum_industry_matches", 0)),
        require_title_or_keyword_match=bool(preferences_raw.get("require_title_or_keyword_match", False)),
        require_industry_match=bool(preferences_raw.get("require_industry_match", False)),
        require_seniority_match=bool(preferences_raw.get("require_seniority_match", False)),
        remote_only_or_phoenix=bool(preferences_raw.get("remote_only_or_phoenix", True)),
        prefer_remote=bool(preferences_raw.get("prefer_remote", True)),
        prefer_phoenix=bool(preferences_raw.get("prefer_phoenix", True)),
        usa_only_remote=bool(preferences_raw.get("usa_only_remote", True)),
        phoenix_metro_terms=[str(item).strip().lower() for item in preferences_raw.get("phoenix_metro_terms", []) if str(item).strip()],
        report_limit=int(preferences_raw.get("report_limit", 100)),
    )

    runtime = RuntimeConfig(
        output_dir=Path(runtime_raw.get("output_dir", "output")),
        sqlite_path=Path(runtime_raw.get("sqlite_path", "data/job_agent.sqlite3")),
        request_timeout_seconds=int(runtime_raw.get("request_timeout_seconds", 25)),
        user_agent=str(runtime_raw.get("user_agent", "JobAgent/0.1")),
    )
    return preferences, runtime


def load_company_boards(path: Path) -> list[CompanyBoard]:
    data = _read_yaml(path)
    boards: list[CompanyBoard] = []
    for provider in ("greenhouse", "lever", "ashby"):
        entries = data.get(provider, []) or []
        for entry in entries:
            if isinstance(entry, str):
                slug = entry.strip()
                label = ""
            else:
                slug = str(entry.get("slug", "")).strip()
                label = str(entry.get("label", "")).strip()
            if slug:
                boards.append(CompanyBoard(provider=provider, slug=slug, label=label))
    return boards


def load_app_config(search_config_path: Path, company_config_path: Path) -> AppConfig:
    preferences, runtime = load_search_config(search_config_path)
    companies = load_company_boards(company_config_path)
    return AppConfig(preferences=preferences, runtime=runtime, companies=companies)
