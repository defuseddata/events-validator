import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../app")))

from helpers import github


def resp(status, payload=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    if status >= 400:
        r.raise_for_status.side_effect = requests.exceptions.HTTPError(f"{status}")
    return r


LISTING = [
    {"name": "b.json", "type": "file"},
    {"name": "a.json", "type": "file"},
    {"name": "repo.json", "type": "file"},
    {"name": "sub", "type": "dir"},
]


@patch.object(github, "is_configured", return_value=True)
@patch.object(github, "_get_headers", return_value={})
class TestListSchemas(unittest.TestCase):
    def setUp(self):
        github.invalidate_schema_list_cache()

    @patch.object(github.requests, "get")
    def test_lists_and_sorts(self, get, *_):
        get.return_value = resp(200, LISTING)
        self.assertEqual(github.list_schemas("x"), ["a.json", "b.json"])

    @patch.object(github.requests, "get")
    def test_404_with_accessible_branch_is_empty(self, get, *_):
        get.side_effect = [resp(404), resp(200, {})]
        self.assertEqual(github.list_schemas("x"), [])

    @patch.object(github.requests, "get")
    def test_404_with_inaccessible_branch_raises(self, get, *_):
        get.side_effect = [resp(404), resp(404)]
        with self.assertRaises(github.GitHubListError):
            github.list_schemas("x")

    @patch.object(github.requests, "get")
    def test_network_error_raises_and_is_not_cached(self, get, *_):
        get.side_effect = requests.exceptions.ConnectionError("down")
        with self.assertRaises(github.GitHubListError):
            github.list_schemas("x", max_age=30)
        get.side_effect = None
        get.return_value = resp(200, LISTING)
        self.assertEqual(github.list_schemas("x", max_age=30), ["a.json", "b.json"])

    @patch.object(github.requests, "get")
    def test_cache_hit_and_invalidation(self, get, *_):
        get.return_value = resp(200, LISTING)
        github.list_schemas("x", max_age=30)
        github.list_schemas("x", max_age=30)
        self.assertEqual(get.call_count, 1)
        github.list_schemas("x")  # max_age=0 always fetches
        self.assertEqual(get.call_count, 2)
        github.invalidate_schema_list_cache()
        github.list_schemas("x", max_age=30)
        self.assertEqual(get.call_count, 3)

    @patch.object(github.requests, "get")
    def test_cache_is_per_branch(self, get, *_):
        get.return_value = resp(200, LISTING)
        github.list_schemas("x", max_age=30)
        github.list_schemas("y", max_age=30)
        self.assertEqual(get.call_count, 2)

    @patch.object(github, "get_file_sha", return_value=None)
    @patch.object(github, "GITHUB_TOKEN", "t")
    @patch.object(github.requests, "put")
    @patch.object(github.requests, "get")
    def test_write_invalidates_cache(self, get, put, *_):
        get.return_value = resp(200, LISTING)
        put.return_value = resp(201, {})
        github.list_schemas("x", max_age=30)
        github.write_schema("new", {}, branch="x")
        github.list_schemas("x", max_age=30)
        self.assertEqual(get.call_count, 2)


@patch.object(github, "is_configured", return_value=True)
@patch.object(github, "_get_headers", return_value={})
class TestAuthHint(unittest.TestCase):
    def setUp(self):
        github.invalidate_schema_list_cache()

    @staticmethod
    def _http_error(status):
        r = resp(status, {})
        r.raise_for_status.side_effect = requests.exceptions.HTTPError(f"{status} Client Error", response=r)
        return r

    def _list_error(self, get, status):
        get.return_value = self._http_error(status)
        with self.assertRaises(github.GitHubListError) as ctx:
            github.list_schemas("x")
        return str(ctx.exception)

    @patch.object(github, "GITHUB_TOKEN", "t")
    @patch.object(github.requests, "get")
    def test_401_says_token_is_invalid_or_expired(self, get, *_):
        msg = self._list_error(get, 401)
        self.assertIn("invalid or has expired", msg)
        self.assertIn("github_token", msg)

    @patch.object(github, "GITHUB_TOKEN", None)
    @patch.object(github.requests, "get")
    def test_missing_token_is_named_on_404_and_401(self, get, *_):
        for status in (404, 401):
            self.assertIn("token is not set", self._list_error(get, status))

    @patch.object(github, "GITHUB_TOKEN", "t")
    @patch.object(github.requests, "get")
    def test_404_with_a_token_points_at_repo_or_scopes(self, get, *_):
        msg = self._list_error(get, 404)
        self.assertIn("404", msg)
        self.assertIn("cannot access this private repository", msg)
        self.assertNotIn("not set", msg)

    @patch.object(github, "GITHUB_TOKEN", None)
    @patch.object(github.requests, "get")
    def test_other_errors_keep_the_original_message(self, get, *_):
        msg = self._list_error(get, 500)
        self.assertIn("500 Client Error", msg)
        self.assertNotIn("not set", msg)
        self.assertNotIn("expired", msg)


if __name__ == "__main__":
    unittest.main()
