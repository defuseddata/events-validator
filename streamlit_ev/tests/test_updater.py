
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add app to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

from helpers.updater import check_schema_health, construct_schema_definition, find_impacted_schemas, rebuild_schema_dry_run

class TestUpdater(unittest.TestCase):

    def test_find_impacted_schemas(self):
        repo = {
            "param1": {"usedInSchemas": ["s1.json", "s2.json"]},
            "param2": {}
        }
        self.assertEqual(find_impacted_schemas("param1", repo), ["s1.json", "s2.json"])
        self.assertEqual(find_impacted_schemas("param2", repo), [])
        self.assertEqual(find_impacted_schemas("missing", repo), [])

    @patch('helpers.updater.read_schema')
    def test_rebuild_schema_dry_run_simple(self, mock_read):
        # Mock schema existing in GCP
        mock_schema = {
            "event_name": {"value": "test"},
            "version": {"value": 1},
            "my_param": {
                "type": "string",
                "value": "initial",
                "description": "old desc",
                "regex": "old regex"
            }
        }
        mock_read.return_value = mock_schema
        
        # New Repo definition
        new_param_data = {
            "type": "string", # same type
            "description": "new desc",
            "regex": "new regex",
            "value": "repo default"
        }
        
        # Act
        orig, new = rebuild_schema_dry_run("s1.json", "my_param", new_param_data)
        
        # Assert
        # 1. Attributes updated
        self.assertEqual(new["my_param"]["description"], "new desc")
        self.assertEqual(new["my_param"]["regex"], "new regex")
        
        # 2. The repo is the source of truth for the value, even when the type is unchanged
        self.assertEqual(new["my_param"]["value"], "repo default")
        
        # 3. Validation of deep copy
        self.assertEqual(orig["my_param"]["description"], "old desc")

    @patch('helpers.updater.read_schema')
    def test_rebuild_schema_dry_run_type_change(self, mock_read):
        # Mock schema 
        mock_schema = {
            "my_param": {
                "type": "string",
                "value": "some string"
            }
        }
        mock_read.return_value = mock_schema
        
        # New Repo definition (type changed)
        new_param_data = {
            "type": "number",
            "value": 42
        }
        
        orig, new = rebuild_schema_dry_run("s1.json", "my_param", new_param_data)
        
        self.assertEqual(new["my_param"]["type"], "number")
        
        # Value logic: in current implementation, if type mismatches, we don't copy old value.
        # So "some string" should NOT be there.
        # It might be 42 (repo default) or empty depending on logic.
        # Logic says: "if new_props[type] == old_type: preserve"
        # Since string != number, it falls through.
        # "elif value in new_param_data: set value"
        self.assertEqual(new["my_param"]["value"], 42)

class TestConstructSchemaDefinitionRegex(unittest.TestCase):

    def test_regex_is_carried_to_the_schema(self):
        props = construct_schema_definition({"type": "string", "description": "d", "regex": r"^T-\d{6}$"})
        self.assertEqual(props["regex"], r"^T-\d{6}$")

    def test_empty_or_missing_regex_is_omitted(self):
        for param in ({"type": "string", "regex": ""}, {"type": "string"}):
            self.assertNotIn("regex", construct_schema_definition(param))

    def test_nested_regex_is_carried_to_the_schema(self):
        props = construct_schema_definition({
            "type": "array",
            "nestedSchema": {
                "sku": {"type": "string", "regex": "^[A-Z]+$"},
                "name": {"type": "string", "regex": ""},
            },
        })
        self.assertEqual(props["nestedSchema"]["sku"]["regex"], "^[A-Z]+$")
        self.assertNotIn("regex", props["nestedSchema"]["name"])

class TestSchemaHealthRegex(unittest.TestCase):

    @staticmethod
    def _health(schema_param, repo_param):
        return check_schema_health({"p": schema_param}, {"p": repo_param})["minor"]

    def test_schema_missing_the_repo_pattern_is_flagged(self):
        self.assertEqual(self._health({"type": "string", "description": "d"},
                                      {"type": "string", "description": "d", "regex": "^a$"}), ["p"])

    def test_different_pattern_is_flagged(self):
        self.assertEqual(self._health({"type": "string", "description": "d", "regex": "^a$"},
                                      {"type": "string", "description": "d", "regex": "^b$"}), ["p"])

    def test_pattern_the_repo_does_not_have_is_flagged(self):
        self.assertEqual(self._health({"type": "string", "description": "d", "regex": "^a$"},
                                      {"type": "string", "description": "d", "regex": ""}), ["p"])

    def test_same_pattern_or_no_pattern_is_healthy(self):
        for schema_param, repo_param in (
            ({"type": "string", "description": "d", "regex": "^a$"}, {"type": "string", "description": "d", "regex": "^a$"}),
            ({"type": "string", "description": "d"}, {"type": "string", "description": "d", "regex": ""}),
            ({"type": "string", "description": "d"}, {"type": "string", "description": "d"}),
        ):
            self.assertEqual(self._health(schema_param, repo_param), [])

    def test_nested_pattern_mismatch_is_flagged(self):
        repo_param = {"type": "array", "description": "d",
                      "nestedSchema": {"sku": {"type": "string", "description": "s", "regex": "^[A-Z]+$"}}}
        stale = {"type": "array", "description": "d",
                 "nestedSchema": {"sku": {"type": "string", "description": "s"}}}
        synced = construct_schema_definition(repo_param)
        self.assertEqual(self._health(stale, repo_param), ["p"])
        self.assertEqual(self._health(synced, repo_param), [])

if __name__ == '__main__':
    unittest.main()
