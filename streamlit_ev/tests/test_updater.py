
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add app to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

from helpers.updater import find_impacted_schemas, rebuild_schema_dry_run

class TestUpdater(unittest.TestCase):

    def test_find_impacted_schemas(self):
        repo = {
            "param1": {"usedInSchemas": ["s1.json", "s2.json"]},
            "param2": {}
        }
        self.assertEqual(find_impacted_schemas("param1", repo), ["s1.json", "s2.json"])
        self.assertEqual(find_impacted_schemas("param2", repo), [])
        self.assertEqual(find_impacted_schemas("missing", repo), [])

    @patch('helpers.updater.readSchemaToJson')
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
        
        # 2. Value preserved because type matched and it existed
        self.assertEqual(new["my_param"]["value"], "initial")
        
        # 3. Validation of deep copy
        self.assertEqual(orig["my_param"]["description"], "old desc")

    @patch('helpers.updater.readSchemaToJson')
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

if __name__ == '__main__':
    unittest.main()
