from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from job_agent.config import SearchPreferences
from job_agent.resume import ResumeProfile
from job_agent.sources import JobListing


@dataclass
class RankedJob:
    rank_key: str
    score: float
    reasons: list[str]
    is_new: bool
    listing: JobListing


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9][a-z0-9\+\#\.\-/]{1,}", text.lower()))


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _contains_phrase(text: str, phrase: str) -> bool:
    phrase = _normalize(phrase)
    if not phrase:
        return False
    return phrase in text


def _build_rank_key(job: JobListing) -> str:
    raw = f"{job.source}|{job.external_id}|{job.company}|{job.title}|{job.url}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _is_remote(job: JobListing) -> bool:
    haystack = " ".join([job.title, job.location, job.description, " ".join(job.tags)]).lower()
    blockers = ("hybrid", "on-site", "onsite")
    if any(blocker in haystack for blocker in blockers):
        return False
    return job.remote or "remote" in haystack or "work from home" in haystack


def _is_phoenix(job: JobListing, preferences: SearchPreferences) -> bool:
    haystack = " ".join([job.location, job.description]).lower()
    return any(term in haystack for term in preferences.phoenix_metro_terms)


def _is_usa_friendly_remote(job: JobListing) -> bool:
    haystack = _normalize(" ".join([job.location, job.description, " ".join(job.tags)]))
    if "remote" not in haystack and not job.remote:
        return False
    restricted_terms = (
        "europe only",
        "uk only",
        "emea",
        "apac",
        "germany only",
        "canada only",
        "latam",
        "latin america",
        "asia",
        "europe",
        "worldwide",
        "global except",
        "kuala lumpur",
        "krakow",
        "poland",
        "brazil",
        "argentina",
        "india",
        "philippines",
    )
    allowed_terms = (
        "united states",
        "u.s.",
        "u.s.a.",
        "usa",
        "us only",
        "us remote",
        "remote usa",
        "anywhere in the us",
        "arizona",
        "phoenix",
    )
    if any(term in haystack for term in restricted_terms):
        return any(term in haystack for term in allowed_terms)
    return True


def _days_old(job: JobListing) -> int | None:
    if not job.posted_at:
        return None
    now = datetime.now(timezone.utc)
    return max((now - job.posted_at).days, 0)


def filter_and_rank_jobs(jobs: list[JobListing], resume: ResumeProfile, preferences: SearchPreferences, limit: int) -> list[RankedJob]:
    deduped: dict[str, JobListing] = {}
    for job in jobs:
        dedupe_key = _normalize(f"{job.company}|{job.title}|{job.url}")
        existing = deduped.get(dedupe_key)
        if existing is None or (job.description and not existing.description):
            deduped[dedupe_key] = job

    ranked: list[RankedJob] = []
    for job in deduped.values():
        remote = _is_remote(job)
        phoenix = _is_phoenix(job, preferences)

        if preferences.remote_only_or_phoenix and not (remote or phoenix):
            continue
        if preferences.usa_only_remote and remote and not phoenix and not _is_usa_friendly_remote(job):
            continue

        title_text = _normalize(job.title)
        full_text = _normalize(" ".join([job.title, job.description, job.location, " ".join(job.tags), job.company]))
        body_tokens = _tokenize(full_text)

        matched_resume_terms = sorted(resume.token_set.intersection(body_tokens))
        matched_boost_terms = sorted(term for term in preferences.boost_keywords if _contains_phrase(full_text, term))
        matched_title_targets = sorted(title for title in preferences.target_titles if _contains_phrase(title_text, title))
        matched_industries = sorted(term for term in preferences.preferred_industries if _contains_phrase(full_text, term))
        matched_seniority_terms = sorted(term for term in preferences.preferred_seniority_terms if _contains_phrase(title_text, term))
        blocked_terms = [term for term in preferences.avoid_keywords if _contains_phrase(full_text, term)]
        if blocked_terms:
            continue
        if preferences.require_title_or_keyword_match and not matched_title_targets and len(matched_boost_terms) < preferences.minimum_keyword_matches:
            continue
        if preferences.require_industry_match and len(matched_industries) < preferences.minimum_industry_matches:
            continue
        if preferences.require_seniority_match and not matched_seniority_terms:
            continue

        score = 0.0
        reasons: list[str] = []

        overlap_score = min(len(matched_resume_terms) * 1.2, 20.0)
        score += overlap_score
        if matched_resume_terms:
            reasons.append(f"resume overlap: {', '.join(matched_resume_terms[:5])}")

        title_score = min(len(matched_title_targets) * 18.0, 36.0)
        score += title_score
        if matched_title_targets:
            reasons.append(f"title match: {', '.join(matched_title_targets[:2])}")

        boost_score = min(len(matched_boost_terms) * 6.0, 36.0)
        score += boost_score
        if matched_boost_terms:
            reasons.append(f"preferred skills: {', '.join(matched_boost_terms[:4])}")

        industry_score = min(len(matched_industries) * 8.0, 24.0)
        score += industry_score
        if matched_industries:
            reasons.append(f"industry fit: {', '.join(matched_industries[:3])}")

        seniority_score = min(len(matched_seniority_terms) * 10.0, 20.0)
        score += seniority_score
        if matched_seniority_terms:
            reasons.append(f"seniority fit: {', '.join(matched_seniority_terms[:2])}")

        if remote and preferences.prefer_remote:
            score += 18.0
            reasons.append("fully remote fit")

        if phoenix and preferences.prefer_phoenix:
            score += 14.0
            reasons.append("Phoenix metro fit")

        age_days = _days_old(job)
        if age_days is not None:
            freshness = max(0.0, 12.0 - math.log2(age_days + 1) * 4.0)
            score += freshness
            reasons.append(f"fresh posting ({age_days}d old)")

        if job.source in {"greenhouse", "lever"}:
            score += 4.0

        ranked.append(
            RankedJob(
                rank_key=_build_rank_key(job),
                score=round(score, 2),
                reasons=reasons[:4],
                is_new=False,
                listing=job,
            )
        )

    ranked.sort(
        key=lambda item: (
            item.score,
            item.listing.posted_at or datetime.min.replace(tzinfo=timezone.utc),
            item.listing.company.lower(),
            item.listing.title.lower(),
        ),
        reverse=True,
    )
    return ranked[:limit]
