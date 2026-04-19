import os
import pytest
from unittest.mock import patch, MagicMock, call


class TestProcessIncident:
    def _run(self, data, playbook=None, ai_text="AI result",
             metric_val="75.0%", screenshot_path=None):
        with patch("core.engine.load_playbook", return_value=playbook) as mock_pb, \
             patch("core.engine.capture_dashboard", return_value=screenshot_path) as mock_ss, \
             patch("core.engine.fetch_grafana_metric", return_value=metric_val) as mock_metric, \
             patch("core.engine.get_ai_analysis", return_value=ai_text) as mock_ai, \
             patch("core.engine.send_email_report") as mock_email, \
             patch("os.path.exists", return_value=bool(screenshot_path)), \
             patch("os.remove"):
            from core.engine import process_incident
            process_incident(data)
            return mock_pb, mock_ss, mock_metric, mock_ai, mock_email

    def test_resolved_alert_skipped(self, grafana_webhook_payload):
        # payload has one firing + one resolved alert
        _, _, _, mock_ai, _ = self._run(grafana_webhook_payload, playbook=None)
        # only the firing alert triggers AI — resolved is skipped
        assert mock_ai.call_count == 1

    def test_capture_screenshot_action_calls_service(self, firing_alert, sample_playbook):
        data = {"alerts": [firing_alert]}
        _, mock_ss, _, _, _ = self._run(data, playbook=sample_playbook)
        mock_ss.assert_called_once()

    def test_fetch_metrics_action_calls_service(self, firing_alert, sample_playbook):
        data = {"alerts": [firing_alert]}
        _, _, mock_metric, _, _ = self._run(data, playbook=sample_playbook)
        # playbook has 2 fetch_metrics actions
        assert mock_metric.call_count == 2

    def test_ai_analysis_action_calls_service(self, firing_alert, sample_playbook):
        data = {"alerts": [firing_alert]}
        _, _, _, mock_ai, _ = self._run(data, playbook=sample_playbook)
        mock_ai.assert_called_once()

    def test_instruction_passed_to_ai(self, firing_alert, sample_playbook):
        data = {"alerts": [firing_alert]}
        _, _, _, mock_ai, _ = self._run(data, playbook=sample_playbook)
        _, kwargs = mock_ai.call_args
        assert kwargs.get("instruction") == sample_playbook["instruction"]

    def test_send_notification_action_sends_email(self, firing_alert, sample_playbook):
        data = {"alerts": [firing_alert]}
        _, _, _, _, mock_email = self._run(data, playbook=sample_playbook)
        mock_email.assert_called_once()

    def test_fallback_runs_when_no_playbook(self, firing_alert):
        data = {"alerts": [firing_alert]}
        _, _, _, mock_ai, mock_email = self._run(data, playbook=None)
        mock_ai.assert_called_once()
        mock_email.assert_called_once()

    def test_fallback_email_subject_contains_alert_name(self, firing_alert):
        data = {"alerts": [firing_alert]}
        _, _, _, _, mock_email = self._run(data, playbook=None)
        subject_arg = mock_email.call_args[0][0]
        assert "HighCPUUsage" in subject_arg

    def test_screenshot_cleanup_on_success(self, firing_alert, sample_playbook):
        data = {"alerts": [firing_alert]}
        with patch("core.engine.load_playbook", return_value=sample_playbook), \
             patch("core.engine.capture_dashboard", return_value="snap.png"), \
             patch("core.engine.fetch_grafana_metric", return_value="50%"), \
             patch("core.engine.get_ai_analysis", return_value="ok"), \
             patch("core.engine.send_email_report"), \
             patch("os.path.exists", return_value=True), \
             patch("os.remove") as mock_remove:
            from core.engine import process_incident
            process_incident(data)
            mock_remove.assert_called_once_with("snap.png")

    def test_screenshot_cleanup_even_if_email_fails(self, firing_alert, sample_playbook):
        data = {"alerts": [firing_alert]}
        with patch("core.engine.load_playbook", return_value=sample_playbook), \
             patch("core.engine.capture_dashboard", return_value="snap.png"), \
             patch("core.engine.fetch_grafana_metric", return_value="50%"), \
             patch("core.engine.get_ai_analysis", return_value="ok"), \
             patch("core.engine.send_email_report", side_effect=Exception("SMTP down")), \
             patch("os.path.exists", return_value=True), \
             patch("os.remove") as mock_remove:
            from core.engine import process_incident
            # exception propagates after finally; cleanup must still run
            with pytest.raises(Exception, match="SMTP down"):
                process_incident(data)
            mock_remove.assert_called_once_with("snap.png")

    def test_no_alerts_key_triggers_test_email(self):
        _, _, _, _, mock_email = self._run({})
        mock_email.assert_called_once()
        subject = mock_email.call_args[0][0]
        assert "TEST" in subject or "Online" in subject
