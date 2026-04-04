# SPDX-FileCopyrightText: 2026 Jiri Vyskocil
# SPDX-License-Identifier: Apache-2.0

"""Story: CLI end-to-end.

The ``terok-dbus-notify`` command-line tool must send a real notification
and print its server-assigned ID, or print ``0`` when no bus is available.
"""

import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.needs_dbus, pytest.mark.needs_notification_daemon]


class TestCliIntegration:
    """End-to-end CLI tests against a real session bus."""

    def test_notify_prints_positive_id(self, dbus_session: str, notification_daemon: None):
        """CLI prints a positive integer notification ID."""
        result = subprocess.run(
            [sys.executable, "-m", "terok_dbus._cli", "CLI test", "Body text"],
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "DBUS_SESSION_BUS_ADDRESS": dbus_session},
        )
        assert result.returncode == 0
        nid = int(result.stdout.strip())
        assert nid > 0

    def test_timeout_flag_accepted(self, dbus_session: str, notification_daemon: None):
        """CLI accepts -t/--timeout and still produces a valid ID."""
        result = subprocess.run(
            [sys.executable, "-m", "terok_dbus._cli", "-t", "1000", "Timeout test"],
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "DBUS_SESSION_BUS_ADDRESS": dbus_session},
        )
        assert result.returncode == 0
        nid = int(result.stdout.strip())
        assert nid > 0

    def test_body_is_optional(self, dbus_session: str, notification_daemon: None):
        """CLI works with summary only (no body argument)."""
        result = subprocess.run(
            [sys.executable, "-m", "terok_dbus._cli", "Summary only"],
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "DBUS_SESSION_BUS_ADDRESS": dbus_session},
        )
        assert result.returncode == 0
        nid = int(result.stdout.strip())
        assert nid > 0
