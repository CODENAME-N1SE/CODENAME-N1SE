import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime

USERNAME = "CODENAME-N1SE"
PROFILE_REPO = "CODENAME-N1SE"
README_FILE = "README.md"

CURRENT_START = "<!-- CURRENTLY_BUILDING:START -->"
CURRENT_END = "<!-- CURRENTLY_BUILDING:END -->"
PROJECTS_START = "<!-- LATEST_PROJECTS:START -->"
PROJECTS_END = "<!-- LATEST_PROJECTS:END -->"

MAX_PROJECTS = 4


def github_request(url):
    token = os.environ.get("GITHUB_TOKEN")

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "CODENAME-N1SE-Profile-Updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        print(f"GitHub API error: {error.code} {error.reason}")
        raise
    except urllib.error.URLError as error:
        print(f"Network error: {error.reason}")
        raise


def get_repositories():
    url = (
        f"https://api.github.com/users/{USERNAME}/repos"
        "?per_page=100&sort=pushed&direction=desc"
    )

    repositories = github_request(url)
    filtered = []

    for repo in repositories:
        if repo.get("fork"):
            continue
        if repo.get("name", "").lower() == PROFILE_REPO.lower():
            continue
        if repo.get("archived"):
            continue
        filtered.append(repo)

    filtered.sort(
        key=lambda repo: repo.get("pushed_at") or "",
        reverse=True,
    )
    return filtered


def get_topics(repo_name):
    url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/topics"
    data = github_request(url)
    return data.get("names", [])


def clean_description(description):
    if not description:
        return "No description provided yet."

    description = " ".join(description.split())
    description = description.replace("<!--", "&lt;!--")
    description = description.replace("-->", "--&gt;")
    return description


def format_date(date_string):
    if not date_string:
        return "UNKNOWN"

    try:
        date = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        return date.strftime("%d %b %Y").upper()
    except ValueError:
        return "UNKNOWN"


def language_label(repo):
    return repo.get("language") or "Multiple / Not detected"


def display_name(repo_name):
    return repo_name.replace("-", " ").replace("_", " ")


def repo_button(repo, color="00ffff"):
    url = repo["html_url"]
    return (
        f'[![Repository]'
        f'(https://img.shields.io/badge/ACCESS_REPOSITORY-{color}'
        f'?style=for-the-badge&logo=github&logoColor=black)]'
        f'({url})'
    )


def build_current_project(repositories):
    active_projects = []

    for repo in repositories:
        try:
            topics = get_topics(repo["name"])
        except Exception as error:
            print(f'Could not retrieve topics for {repo["name"]}: {error}')
            topics = repo.get("topics", [])

        normalized_topics = [topic.lower() for topic in topics]

        if "currently-building" in normalized_topics:
            active_projects.append(repo)

    if not active_projects:
        return """`NO ACTIVE PROJECT DETECTED`

Add the `currently-building` topic to the repository you are actively developing."""

    active_projects.sort(
        key=lambda repo: repo.get("pushed_at") or "",
        reverse=True,
    )

    repo = active_projects[0]
    name = display_name(repo["name"]).upper()
    description = clean_description(repo.get("description"))
    language = language_label(repo)
    updated = format_date(repo.get("pushed_at"))

    return f"""### ⚡ {name}

`{language}` • `ACTIVE DEVELOPMENT`

{description}

```text
STATUS       :: BUILDING
LAST SIGNAL  :: {updated}
SOURCE       :: GITHUB
```

{repo_button(repo)}"""


def build_latest_projects(repositories):
    latest = repositories[:MAX_PROJECTS]

    if not latest:
        return "`NO PUBLIC PROJECTS DETECTED`"

    sections = []
    colors = ["00ffff", "8a2be2", "ff00ff", "00ffff"]

    for index, repo in enumerate(latest, start=1):
        name = display_name(repo["name"]).upper()
        description = clean_description(repo.get("description"))
        language = language_label(repo)
        updated = format_date(repo.get("pushed_at"))
        color = colors[(index - 1) % len(colors)]

        section = f"""### `[{index:02}]` ⚡ {name}

```text
LANGUAGE     :: {language}
STATUS       :: PUBLISHED
LAST UPDATE  :: {updated}

DESCRIPTION ::
{description}
```

{repo_button(repo, color)}"""

        sections.append(section)

    project_output = "\n\n<br>\n\n".join(sections)

    project_output += f"""

<br>

```text
N1SE://PROJECT_DATABASE

{len(latest):02} LATEST PROJECTS LOADED

> DATABASE QUERY COMPLETE_
```"""

    return project_output


def replace_section(content, start_marker, end_marker, replacement):
    if start_marker not in content:
        raise RuntimeError(f"Missing README marker: {start_marker}")

    if end_marker not in content:
        raise RuntimeError(f"Missing README marker: {end_marker}")

    pattern = re.escape(start_marker) + r".*?" + re.escape(end_marker)
    new_section = (
        f"{start_marker}\n\n"
        f"{replacement}\n\n"
        f"{end_marker}"
    )

    updated_content, count = re.subn(
        pattern,
        new_section,
        content,
        count=1,
        flags=re.DOTALL,
    )

    if count != 1:
        raise RuntimeError(
            f"Could not safely update README section: {start_marker}"
        )

    return updated_content


def read_readme():
    if not os.path.exists(README_FILE):
        raise FileNotFoundError(f"{README_FILE} was not found.")

    with open(README_FILE, "r", encoding="utf-8") as file:
        return file.read()


def write_readme(content):
    with open(README_FILE, "w", encoding="utf-8") as file:
        file.write(content)


def main():
    print("======================================")
    print("       N1SE PROFILE AUTOMATION")
    print("======================================")

    print("[01] Connecting to GitHub...")
    repositories = get_repositories()

    print(f"[02] Repositories detected: {len(repositories)}")

    print("[03] Detecting currently-building project...")
    current_project = build_current_project(repositories)

    print("[04] Generating latest project database...")
    latest_projects = build_latest_projects(repositories)

    print("[05] Reading README.md...")
    readme = read_readme()

    print("[06] Updating CURRENTLY_BUILDING...")
    readme = replace_section(
        readme,
        CURRENT_START,
        CURRENT_END,
        current_project,
    )

    print("[07] Updating LATEST_PROJECTS...")
    readme = replace_section(
        readme,
        PROJECTS_START,
        PROJECTS_END,
        latest_projects,
    )

    print("[08] Saving README.md...")
    write_readme(readme)

    print("======================================")
    print("       PROFILE UPDATE COMPLETE")
    print("======================================")


if __name__ == "__main__":
    main()
