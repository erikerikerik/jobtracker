from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import requests
from bs4 import BeautifulSoup

from job_agent.config import AppConfig, CompanyBoard


@dataclass
class JobListing:
    source: str
    external_id: str
    title: str
    company: str
    location: str
    url: str
    description: str = ""
    remote: bool = False
    posted_at: datetime | None = None
    employment_type: str = ""
    tags: list[str] = field(default_factory=list)
    salary: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


def _clean_html(html: str) -> str:
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _build_session(app_config: AppConfig) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": app_config.runtime.user_agent,
            "Accept": "application/json, text/html, application/xml;q=0.9, */*;q=0.8",
        }
    )
    return session


def _get_json(session: requests.Session, app_config: AppConfig, url: str) -> object:
    response = session.get(url, timeout=app_config.runtime.request_timeout_seconds)
    response.raise_for_status()
    return response.json()


def fetch_remotive(session: requests.Session, app_config: AppConfig) -> list[JobListing]:
    url = "https://remotive.com/api/remote-jobs"
    data = _get_json(session, app_config, url)
    jobs = []
    for item in data.get("jobs", []):
        jobs.append(
            JobListing(
                source="remotive",
                external_id=str(item.get("id", "")),
                title=str(item.get("title", "")).strip(),
                company=str(item.get("company_name", "")).strip(),
                location=str(item.get("candidate_required_location", "Remote")).strip(),
                url=str(item.get("url", "")).strip(),
                description=_clean_html(item.get("description", "")),
                remote=True,
                posted_at=_parse_datetime(item.get("publication_date")),
                employment_type=str(item.get("job_type", "")).strip(),
                tags=[str(tag).strip() for tag in item.get("tags", []) if str(tag).strip()],
                salary=str(item.get("salary", "")).strip(),
            )
        )
    return jobs


def fetch_remoteok(session: requests.Session, app_config: AppConfig) -> list[JobListing]:
    url = "https://remoteok.com/api"
    data = _get_json(session, app_config, url)
    jobs = []
    for item in data:
        if not isinstance(item, dict) or "id" not in item:
            continue
        tags = [str(tag).strip() for tag in item.get("tags", []) if str(tag).strip()]
        jobs.append(
            JobListing(
                source="remoteok",
                external_id=str(item.get("id", "")),
                title=str(item.get("position", "")).strip(),
                company=str(item.get("company", "")).strip(),
                location=str(item.get("location", "Remote")).strip(),
                url=str(item.get("url", "")).strip(),
                description=_clean_html(item.get("description", "")),
                remote=True,
                posted_at=_parse_datetime(item.get("date")),
                employment_type="",
                tags=tags,
                salary=str(item.get("salary_min", "") or "").strip(),
            )
        )
    return jobs


def fetch_greenhouse(session: requests.Session, app_config: AppConfig, board: CompanyBoard) -> list[JobListing]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board.slug}/jobs?content=true"
    data = _get_json(session, app_config, url)
    jobs = []
    for item in data.get("jobs", []):
        absolute_url = str(item.get("absolute_url", "")).strip()
        if not absolute_url:
            continue
        metadata = {"board_slug": board.slug}
        jobs.append(
            JobListing(
                source="greenhouse",
                external_id=str(item.get("id", "")),
                title=str(item.get("title", "")).strip(),
                company=board.label or board.slug.replace("-", " ").title(),
                location=str(item.get("location", {}).get("name", "")).strip(),
                url=absolute_url,
                description=_clean_html(item.get("content", "")),
                remote="remote" in str(item.get("location", {}).get("name", "")).lower()
                or "remote" in str(item.get("title", "")).lower(),
                posted_at=None,
                employment_type="",
                tags=[],
                salary="",
                metadata=metadata,
            )
        )
    return jobs


def fetch_lever(session: requests.Session, app_config: AppConfig, board: CompanyBoard) -> list[JobListing]:
    url = f"https://api.lever.co/v0/postings/{board.slug}?mode=json"
    data = _get_json(session, app_config, url)
    jobs = []
    for item in data:
        categories = item.get("categories", {}) or {}
        location = str(categories.get("location", "")).strip()
        team = str(categories.get("team", "")).strip()
        commitment = str(categories.get("commitment", "")).strip()
        jobs.append(
            JobListing(
                source="lever",
                external_id=str(item.get("id", "")),
                title=str(item.get("text", "")).strip(),
                company=board.label or board.slug.replace("-", " ").title(),
                location=location,
                url=str(item.get("hostedUrl", "")).strip(),
                description=_clean_html(item.get("descriptionPlain", "") or item.get("description", "")),
                remote="remote" in location.lower() or "remote" in str(item.get("text", "")).lower(),
                posted_at=None,
                employment_type=commitment,
                tags=[value for value in [team, commitment, str(categories.get("workplaceType", "")).strip()] if value],
                salary="",
                metadata={"board_slug": board.slug},
            )
        )
    return jobs


def fetch_ashby(session: requests.Session, app_config: AppConfig, board: CompanyBoard) -> list[JobListing]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board.slug}?includeCompensation=true"
    data = _get_json(session, app_config, url)
    jobs = []
    for item in data.get("jobs", []):
        if not item.get("isListed", True):
            continue
        location = str(item.get("location", "")).strip()
        job_url = str(item.get("jobUrl", "") or item.get("applyUrl", "")).strip()
        if not job_url:
            continue
        department = str(item.get("department", "")).strip()
        team = str(item.get("team", "")).strip()
        compensation = item.get("compensation", {}) or {}
        compensation_summary = str(
            compensation.get("compensationTierSummary", "")
            or compensation.get("scrapeableCompensationSalarySummary", "")
        ).strip()
        secondary_locations = [
            str(loc.get("location", "")).strip()
            for loc in item.get("secondaryLocations", []) or []
            if str(loc.get("location", "")).strip()
        ]
        description_parts = [department, team, compensation_summary, " ".join(secondary_locations)]
        tags = [value for value in [department, team] + secondary_locations if value]
        jobs.append(
            JobListing(
                source="ashby",
                external_id=str(item.get("id", "") or item.get("jobUrl", "")).strip(),
                title=str(item.get("title", "")).strip(),
                company=board.label or board.slug.replace("-", " ").title(),
                location=location,
                url=job_url,
                description=" | ".join(part for part in description_parts if part),
                remote=bool(item.get("isRemote", False)) or "remote" in location.lower(),
                posted_at=None,
                employment_type=str(item.get("employmentType", "")).strip(),
                tags=tags,
                salary=compensation_summary,
                metadata={"board_slug": board.slug},
            )
        )
    return jobs


def fetch_all_jobs(app_config: AppConfig) -> tuple[list[JobListing], list[str]]:
    session = _build_session(app_config)
    listings: list[JobListing] = []
    warnings: list[str] = []

    fetchers: list[tuple[str, callable]] = [
        ("Remotive", lambda: fetch_remotive(session, app_config)),
        ("Remote OK", lambda: fetch_remoteok(session, app_config)),
    ]

    for board in app_config.companies:
        if board.provider == "greenhouse":
            fetchers.append((f"Greenhouse:{board.slug}", lambda board=board: fetch_greenhouse(session, app_config, board)))
        elif board.provider == "lever":
            fetchers.append((f"Lever:{board.slug}", lambda board=board: fetch_lever(session, app_config, board)))
        elif board.provider == "ashby":
            fetchers.append((f"Ashby:{board.slug}", lambda board=board: fetch_ashby(session, app_config, board)))

    for label, fetcher in fetchers:
        try:
            listings.extend(fetcher())
        except requests.RequestException as exc:
            warnings.append(f"{label} fetch failed: {exc}")
        except ValueError as exc:
            warnings.append(f"{label} parse failed: {exc}")

    return listings, warnings
