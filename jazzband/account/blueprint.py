from flask import current_app, flash
from flask_dance.consumer import OAuth2ConsumerBlueprint, oauth_error
from flask_dance.consumer.requests import BaseOAuth2Session, OAuth2Session
from flask_dance.consumer.storage.sqla import SQLAlchemyStorage
from flask_login import current_user, login_user
from sentry_sdk import capture_message, configure_scope
from urlobject import URLObject
from werkzeug.utils import cached_property

from ..cache import cache
from ..db import postgres as db
from ..exceptions import RateLimit
from .models import OAuth


@oauth_error.connect
def github_error(blueprint, error, error_description=None, error_uri=None):
    """A GitHub API error handler that pushes the error to Sentry
    and shows a flash message to the user.
    """
    if error:
        with configure_scope() as scope:
            scope.set_extra("error_description", error_description)
            scope.set_extra("error_uri", error_uri)
            capture_message(f"Error during OAUTH found: {error}")
        flash(
            f"OAuth error from Github ({error}): {error_description}", category="error"
        )


class GitHubSessionMixin:
    """A requests session mixin for GitHub that implements currently:

    - rate limit handling (by raising an exception when it happens)
    - pagination by the additional all_pages parameter
    """

    def request(self, method, url, data=None, headers=None, all_pages=False, **kwargs):
        response = super().request(
            method=method, url=url, data=data, headers=headers, **kwargs
        )

        if response.status_code == 403:
            ratelimit_remaining = response.headers.get("X-RateLimit-Remaining")
            if ratelimit_remaining:
                try:
                    if int(ratelimit_remaining) < 1:
                        raise RateLimit(response=response)
                except ValueError:
                    pass

        if all_pages:
            result = response.json()
            while response.links.get("next"):
                url = response.links["next"]["url"]
                response = super().request(
                    method=method, url=url, data=data, headers=headers, **kwargs
                )
                body = response.json()
                if isinstance(body, list):
                    result += body
                elif isinstance(body, dict) and "items" in body:
                    result["items"] += body["items"]
            return result
        else:
            return response


class GitHubSession(GitHubSessionMixin, OAuth2Session):
    """A custom GitHub session that implements a bunch of GitHub
    API specific functionality (e.g. pagination and rate limit handling)
    """


class AdminGitHubSession(GitHubSessionMixin, BaseOAuth2Session):
    """A custom GitHub session class that uses the blueprint's
    admin access token.
    """

    def __init__(self, blueprint=None, base_url=None, *args, **kwargs):
        token = {"access_token": blueprint.admin_access_token}
        super().__init__(token=token, *args, **kwargs)
        self.blueprint = blueprint
        self.base_url = URLObject(base_url)

    def request(self, method, url, data=None, headers=None, **kwargs):
        if self.base_url:
            url = self.base_url.relative(url)

        return super().request(
            method=method,
            url=url,
            data=data,
            headers=headers,
            client_id=self.blueprint.client_id,
            client_secret=self.blueprint.client_secret,
            **kwargs,
        )


class GitHubBlueprint(OAuth2ConsumerBlueprint):
    """A custom OAuth2 blueprint that implements some of our
    specific GitHub API functions.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(
            base_url="https://api.github.com/",
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            session_class=GitHubSession,
            storage=SQLAlchemyStorage(
                OAuth, db.session, user=current_user, user_required=False, cache=cache
            ),
            *args,
            **kwargs,
        )
        self.from_config.update(
            {
                "client_id": "GITHUB_OAUTH_CLIENT_ID",
                "client_secret": "GITHUB_OAUTH_CLIENT_SECRET",
                "scope": "GITHUB_SCOPE",
                "members_team_id": "GITHUB_MEMBERS_TEAM_ID",
                "roadies_team_id": "GITHUB_ROADIES_TEAM_ID",
                "admin_access_token": "GITHUB_ADMIN_TOKEN",
                "org_id": "GITHUB_ORG_ID",
            }
        )

    @cached_property
    def admin_session(self):
        "This is a custom session using the organization's admin permissions."
        return AdminGitHubSession(
            client_id=self._client_id,
            client=self.client,
            auto_refresh_url=self.auto_refresh_url,
            auto_refresh_kwargs=self.auto_refresh_kwargs,
            scope=self.scope,
            state=self.state,
            blueprint=self,
            base_url=self.base_url,
            **self.kwargs,
        )

    def join_organization(self, user_login):
        """
        Adds the GitHub user with the given login to the org.
        """
        return self.admin_session.put(
            f"teams/{self.members_team_id}/memberships/{user_login}"
        )

    def leave_organization(self, user_login):
        """
        Remove the GitHub user with the given login from the org.
        """
        return self.admin_session.delete(f"orgs/{self.org_id}/memberships/{user_login}")

    def get_projects(self):
        projects = self.admin_session.get(
            f"orgs/{self.org_id}/repos?type=public", all_pages=True
        )
        projects_with_subscribers = []
        for project in projects:
            project_name = project["name"]
            watchers = self.admin_session.get(
                f"repos/jazzband/{project_name}/subscribers", all_pages=True
            )
            project["subscribers_count"] = len(watchers)
            projects_with_subscribers.append(project)
        return projects_with_subscribers

    def get_roadies(self):
        return self.admin_session.get(
            f"teams/{self.roadies_team_id}/members", all_pages=True
        )

    def get_members(self):
        without_2fa_ids = set(user["id"] for user in self.get_without_2fa())
        roadies_ids = set(roadie["id"] for roadie in self.get_roadies())
        all_members = self.admin_session.get(
            f"teams/{self.members_team_id}/members", all_pages=True
        )
        members = []
        for member in all_members:
            member["is_member"] = True
            member["is_roadie"] = member["id"] in roadies_ids
            member["has_2fa"] = member["id"] not in without_2fa_ids
            members.append(member)
        return members

    def publicize_membership(self, user_login):
        """
        Publicizes the membership of the GitHub user with the given login.
        """
        self.admin_session.put(f"orgs/{self.org_id}/public_members/{user_login}")

    def get_emails(self, user):
        """
        Gets the verified email addresses of the authenticated GitHub user.
        """
        with current_app.test_request_context("/"):
            login_user(user)
            return self.session.get("user/emails", all_pages=True)

    def get_without_2fa(self):
        """
        Gets the organization members without Two Factor Auth enabled.
        """
        return self.admin_session.get(
            f"orgs/{self.org_id}/members?filter=2fa_disabled", all_pages=True
        )

    def is_member(self, user_login):
        """
        Checks if the GitHub user with the given login is member of the org.
        """
        try:
            self.admin_session.get(f"orgs/{self.org_id}/members/{user_login}")
            return True
        except Exception:
            return False

    def new_roadies_issue(self, data):
        return self.new_project_issue(org="jazzband-roadies", project="help", data=data)

    def new_project_issue(self, project, data, org="jazzband"):
        return self.admin_session.post(f"repos/{org}/{project}/issues", json=data)
