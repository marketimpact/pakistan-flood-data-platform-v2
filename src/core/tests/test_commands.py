from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from unittest.mock import patch


class CollectDataCommandTests(TestCase):
    @patch("core.services.data_collection.update_gauges_from_api")
    def test_collect_data_command_calls_service(self, mock_update_gauges):
        """
        Test that the collect_data command correctly calls the
        update_gauges_from_api service function.
        """
        # Create a mock API response to be returned by the service
        mock_update_gauges.return_value = None

        out = StringIO()
        call_command("collect_data", stdout=out)

        # Check that our service function was called
        mock_update_gauges.assert_called_once()

        # Check that the command outputs a success message
        self.assertIn("Successfully collected data.", out.getvalue())
