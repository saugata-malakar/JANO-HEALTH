"""
Claim Verification Engine.

Checks the candidate's public links against reality:

  GITHUB
    - Profile exists?
    - Account age, follower count, public repo count
    - Recent commit cadence (last 90 days, via events API)
    - Top languages across pinned/recent repos
    - Authenticity heuristic 0-100 — combines age, activity, repo count
    - Flags suspicious profiles (created last week, zero commits, etc.)

  LINKEDIN
    - URL well-formedness only. We DO NOT scrape — LinkedIn forbids it.
    - We extract the slug and confirm it follows /in/<slug> conventions.
    - For deeper validation, the prod system would integrate a paid
      provider like Proxycurl (noted in the system design doc).

  CROSS-REFERENCE
    - Compare GitHub bio / repo languages against resume's claimed skills.
    - Flag mismatches (e.g. resume says Go, GitHub is 100% PHP).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.models.resume import ParsedResume
from app.models.scoring import (
    GitHubVerification,
    LinkedInVerification,
    VerificationResult,
)

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
HTTP_TIMEOUT = 15.0


class VerificationEngine:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def verify(self, resume: ParsedResume) -> VerificationResult:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            github = await self._verify_github(client, resume.links.github)
            linkedin = self._verify_linkedin(resume.links.linkedin)

        cross_ref = self._cross_reference(resume, github)

        # Overall authenticity is github-weighted because it's the only signal
        # we can actually verify. If GitHub wasn't present, fall back to a
        # neutral 50 — meaning "we can't tell".
        if github.found:
            overall = github.authenticity_score
            if cross_ref:
                overall = max(0, overall - 5 * len(cross_ref))
        else:
            overall = 50.0

        return VerificationResult(
            github=github,
            linkedin=linkedin,
            cross_reference=cross_ref,
            overall_authenticity=round(overall, 1),
        )

    # -- GitHub ----------------------------------------------------------

    async def _verify_github(
        self, client: httpx.AsyncClient, github_url: str | None
    ) -> GitHubVerification:
        if not github_url:
            return GitHubVerification(found=False, notes=["No GitHub URL on resume."])

        username = _extract_github_username(github_url)
        if not username:
            return GitHubVerification(
                found=False,
                profile_url=github_url,
                notes=["GitHub URL is malformed."],
            )

        headers = {"Accept": "application/vnd.github+json"}
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"

        # Profile
        try:
            r = await client.get(f"{GITHUB_API}/users/{username}", headers=headers)
        except httpx.HTTPError as e:
            logger.warning("GitHub network error for %s: %s", username, e)
            return GitHubVerification(
                found=False,
                username=username,
                profile_url=github_url,
                notes=[f"Network error contacting GitHub: {e}"],
            )

        if r.status_code == 404:
            return GitHubVerification(
                found=False,
                username=username,
                profile_url=github_url,
                notes=["GitHub user does not exist (404)."],
                flags=["profile_not_found"],
            )
        if r.status_code == 403:
            return GitHubVerification(
                found=False,
                username=username,
                profile_url=github_url,
                notes=["GitHub rate-limited. Set GITHUB_TOKEN to raise the limit to 5000/hr."],
                flags=["rate_limited"],
            )
        if r.status_code != 200:
            return GitHubVerification(
                found=False,
                username=username,
                profile_url=github_url,
                notes=[f"GitHub returned status {r.status_code}."],
            )

        profile = r.json()
        created_at = _parse_iso(profile.get("created_at"))
        age_days = (datetime.now(timezone.utc) - created_at).days if created_at else 0

        # Recent activity (events) — last 100 events, public only
        events_resp = await client.get(
            f"{GITHUB_API}/users/{username}/events/public",
            headers=headers,
            params={"per_page": 100},
        )
        push_event_count = 0
        if events_resp.status_code == 200:
            for ev in events_resp.json():
                if ev.get("type") != "PushEvent":
                    continue
                created = _parse_iso(ev.get("created_at"))
                if not created:
                    continue
                age = (datetime.now(timezone.utc) - created).days
                if age <= 90:
                    # Each PushEvent can contain multiple commits
                    push_event_count += len(ev.get("payload", {}).get("commits", []) or [1])

        # Top repos (newest 30)
        repos_resp = await client.get(
            f"{GITHUB_API}/users/{username}/repos",
            headers=headers,
            params={"per_page": 30, "sort": "updated"},
        )
        top_languages: list[str] = []
        pinned_names: list[str] = []
        if repos_resp.status_code == 200:
            repos = repos_resp.json()
            lang_counts: dict[str, int] = {}
            for repo in repos:
                if repo.get("fork"):
                    continue  # forks don't count as authored work
                lang = repo.get("language")
                if lang:
                    lang_counts[lang] = lang_counts.get(lang, 0) + 1
                pinned_names.append(repo.get("name") or "")
            top_languages = sorted(lang_counts, key=lang_counts.get, reverse=True)[:5]
            pinned_names = pinned_names[:6]

        # Authenticity heuristic
        score, flags, notes = _github_authenticity(
            age_days=age_days,
            public_repos=profile.get("public_repos", 0),
            followers=profile.get("followers", 0),
            recent_pushes=push_event_count,
            has_bio=bool(profile.get("bio")),
        )

        return GitHubVerification(
            found=True,
            username=username,
            profile_url=profile.get("html_url") or github_url,
            public_repos=profile.get("public_repos", 0),
            followers=profile.get("followers", 0),
            account_age_days=age_days,
            recent_commit_count_90d=push_event_count,
            top_languages=top_languages,
            pinned_repo_names=[n for n in pinned_names if n],
            authenticity_score=score,
            flags=flags,
            notes=notes,
        )

    # -- LinkedIn --------------------------------------------------------

    def _verify_linkedin(self, url: str | None) -> LinkedInVerification:
        if not url:
            return LinkedInVerification(
                found=False,
                notes=["No LinkedIn URL on resume."],
            )
        parsed = urlparse(url if "://" in url else f"https://{url}")
        host_ok = "linkedin.com" in (parsed.netloc or "").lower()
        path = parsed.path or ""
        m = re.match(r"^/in/([a-zA-Z0-9\-_%]+)/?$", path)
        if host_ok and m:
            slug = m.group(1)
            return LinkedInVerification(
                found=True,
                profile_url=url,
                url_valid=True,
                slug=slug,
                notes=[
                    "URL is well-formed. Note: LinkedIn forbids automated scraping; "
                    "deep verification requires a paid provider (e.g. Proxycurl)."
                ],
            )
        return LinkedInVerification(
            found=True,
            profile_url=url,
            url_valid=False,
            notes=["URL does not match LinkedIn's /in/<slug> pattern."],
        )

    # -- Cross-reference -------------------------------------------------

    def _cross_reference(
        self, resume: ParsedResume, github: GitHubVerification
    ) -> list[str]:
        """Surface red flags between the resume's claims and GitHub reality."""
        flags: list[str] = []
        if not github.found or not github.top_languages:
            return flags

        gh_langs = {l.lower() for l in github.top_languages}
        resume_langs = {s.lower() for s in resume.skills}

        # Identify "language" skills only (avoids false alarms on tools)
        known_langs = {
            "python", "java", "javascript", "typescript", "go", "rust",
            "c++", "c#", "ruby", "php", "swift", "kotlin", "scala",
        }
        resume_prog_langs = resume_langs & known_langs
        if not resume_prog_langs:
            return flags

        # If candidate claims langs but NONE appear in GitHub top 5
        if not (resume_prog_langs & gh_langs):
            flags.append(
                f"Resume claims {', '.join(sorted(resume_prog_langs))} but GitHub top "
                f"languages are {', '.join(github.top_languages)}."
            )

        if github.recent_commit_count_90d == 0 and github.account_age_days > 365:
            flags.append("GitHub account exists >1yr but shows 0 public commits in last 90 days.")

        return flags


# -- helpers ------------------------------------------------------------


def _extract_github_username(url: str) -> str | None:
    """github.com/foo, https://github.com/foo, foo all → 'foo'."""
    if "github.com" in url:
        m = re.search(r"github\.com/([A-Za-z0-9][A-Za-z0-9-]*)/?", url)
        return m.group(1) if m else None
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", url.strip()):
        return url.strip()
    return None


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _github_authenticity(
    *,
    age_days: int,
    public_repos: int,
    followers: int,
    recent_pushes: int,
    has_bio: bool,
) -> tuple[float, list[str], list[str]]:
    """Compute a 0-100 authenticity score with flags + notes."""
    flags: list[str] = []
    notes: list[str] = []
    score = 0.0

    # Account age — anything > 2yr maxes out
    if age_days >= 730:
        score += 30
        notes.append(f"Account age {age_days} days (mature).")
    elif age_days >= 180:
        score += 20
        notes.append(f"Account age {age_days} days.")
    elif age_days >= 30:
        score += 10
        flags.append("account_under_6_months")
    else:
        flags.append("account_under_30_days")
        notes.append(f"Account is only {age_days} days old.")

    # Repo count
    if public_repos >= 10:
        score += 25
    elif public_repos >= 3:
        score += 15
    elif public_repos >= 1:
        score += 5
    else:
        flags.append("zero_public_repos")

    # Recent activity — last 90 days
    if recent_pushes >= 30:
        score += 30
        notes.append(f"{recent_pushes} commits in last 90 days (active).")
    elif recent_pushes >= 5:
        score += 18
    elif recent_pushes >= 1:
        score += 8
    else:
        flags.append("no_recent_activity_90d")

    # Followers — soft signal
    if followers >= 50:
        score += 10
    elif followers >= 5:
        score += 5

    # Bio
    if has_bio:
        score += 5

    return min(100.0, score), flags, notes
