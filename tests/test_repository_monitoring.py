"""Offline tests for repository discussion collection and notifications."""

from datetime import datetime
from types import SimpleNamespace


class FakeRepo:
    has_discussions = True
    name = "monitor"
    description = "Repository monitor"
    fork = False
    forks_count = 2
    stargazers_count = 3
    subscribers_count = 1
    html_url = "https://github.example/owner/monitor"
    language = "Python"
    created_at = datetime(2025, 1, 1)
    updated_at = datetime(2026, 7, 25)

    # Initializes a repository double with supplied discussions
    def __init__(self, discussions):
        self.discussions = discussions
        self.discussion_schema = None
        self.discussion_states = None

    # Returns an empty stargazer collection
    def get_stargazers(self):
        return []

    # Returns an empty subscriber collection
    def get_subscribers(self):
        return []

    # Returns an empty fork collection
    def get_forks(self):
        return []

    # Returns an empty issue collection
    def get_issues(self, state):
        assert state == "open"
        return []

    # Returns an empty pull request collection
    def get_pulls(self, state):
        assert state == "open"
        return []

    # Records the GraphQL request and returns supplied discussions
    def get_discussions(self, schema, states):
        self.discussion_schema = schema
        self.discussion_states = states
        return self.discussions


class FakeEventRepo:
    id = 1
    name = "owner/monitor"
    url = "https://api.github.example/repos/owner/monitor"


class FakeGithub:
    # Returns minimal repository details for event rendering
    def get_repo(self, name):
        assert name == "owner/monitor"
        return SimpleNamespace(full_name=name, html_url="https://github.example/owner/monitor", description="Repository monitor")


# Builds a discussion object matching PyGithub GraphQL attributes
def _discussion(number=7, author: str | None = "octocat"):
    author_object = SimpleNamespace(login=author) if author else None
    return SimpleNamespace(number=number, title="How should this work?", author=author_object, url=f"https://github.example/owner/monitor/discussions/{number}")


# Confirms repositories without Discussions return an empty baseline
def test_disabled_discussions_return_empty_baseline(gm_module):
    repo = FakeRepo([])
    repo.has_discussions = False
    assert gm_module.github_get_repo_discussions(repo) == (0, [])
    assert repo.discussion_schema is None


# Confirms open discussions are queried and formatted like issues
def test_open_discussions_are_formatted(gm_module):
    repo = FakeRepo([_discussion(), _discussion(number=8, author=None)])
    count, items = gm_module.github_get_repo_discussions(repo)
    assert count == 2
    assert repo.discussion_states == ["OPEN"]
    assert repo.discussion_schema is not None
    assert "number title url" in repo.discussion_schema
    assert items == [
        "#7 How should this work? (octocat) [ https://github.example/owner/monitor/discussions/7 ]",
        "#8 How should this work? (ghost) [ https://github.example/owner/monitor/discussions/8 ]",
    ]


# Confirms repository snapshots include discussion state beside issues and pulls
def test_repository_snapshot_includes_discussions(gm_module):
    repo = FakeRepo([_discussion()])
    result = gm_module.github_process_repos([repo], show_progress=False, fetch_identity_lists=False)
    assert result[0]["discussions"] == 1
    assert result[0]["discussions_list"] == ["#7 How should this work? (octocat) [ https://github.example/owner/monitor/discussions/7 ]"]


# Confirms newly opened discussions generate repository notifications with links
def test_opened_discussion_sends_repository_notification(gm_module, monkeypatch, capsys):
    emails = []
    item = "#7 How should this work? (octocat) [ https://github.example/owner/monitor/discussions/7 ]"
    monkeypatch.setattr(gm_module, "REPO_NOTIFICATION", True)
    monkeypatch.setattr(gm_module, "send_email", lambda *args, **kwargs: emails.append((args, kwargs)) or 0)
    gm_module.check_repo_list_changes(0, 1, [], [item], "Discussions", "monitor", "https://github.example/owner/monitor", "owner", "")
    output = capsys.readouterr().out
    assert "Added discussions" in output
    assert emails[0][0][0] == "GitHub user owner number of discussions for repo 'monitor' has changed! (+1, 0 -> 1)"
    assert '<a href="https://github.example/owner/monitor/discussions/7">' in emails[0][0][2]


# Confirms removed open discussions are described as closed
def test_removed_discussion_is_described_as_closed(gm_module, capsys):
    item = "#7 How should this work? (octocat) [ https://github.example/owner/monitor/discussions/7 ]"
    gm_module.check_repo_list_changes(1, 0, [item], [], "Discussions", "monitor", "https://github.example/owner/monitor", "owner", "")
    assert "Closed discussions" in capsys.readouterr().out


# Confirms DiscussionEvent payload details remain readable
def test_discussion_event_formatting(gm_module, capsys):
    event = SimpleNamespace(created_at=datetime(2026, 7, 25), id="event-1", type="DiscussionEvent", repo=FakeEventRepo(), actor=SimpleNamespace(login="octocat", name=None, html_url="https://github.example/octocat"), payload={"action": "created", "discussion": {"title": "How should this work?", "html_url": "https://github.example/owner/monitor/discussions/7", "category": {"name": "Ideas"}}})
    _, _, _, text = gm_module.github_print_event(event, FakeGithub())
    capsys.readouterr()
    assert "Discussion title:\t\tHow should this work?" in text
    assert "Discussion category:\t\tIdeas" in text


# Confirms discussion comment payloads remain readable when a backend supplies them
def test_discussion_comment_event_formatting(gm_module, capsys):
    event = SimpleNamespace(created_at=datetime(2026, 7, 25), id="event-2", type="DiscussionCommentEvent", repo=FakeEventRepo(), actor=SimpleNamespace(login="octocat", name=None, html_url="https://github.example/octocat"), payload={"action": "created", "comment": {"user": {"login": "octocat"}, "body": "A useful reply"}})
    _, _, _, text = gm_module.github_print_event(event, FakeGithub())
    capsys.readouterr()
    assert "Discussion comment by:\t\toctocat" in text
    assert "A useful reply" in text
