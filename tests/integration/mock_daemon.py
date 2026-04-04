# SPDX-FileCopyrightText: 2026 Jiri Vyskocil
# SPDX-License-Identifier: Apache-2.0

"""Minimal freedesktop Notifications daemon for integration tests.

Implements just enough of the spec to accept ``Notify`` calls, return
incrementing IDs, and emit ``ActionInvoked`` / ``NotificationClosed``
signals.  Runs entirely in-process via dbus-fast — no external binary.
"""

from dbus_fast.aio import MessageBus
from dbus_fast.service import ServiceInterface, method, signal

from terok_dbus._constants import BUS_NAME, INTERFACE_NAME, OBJECT_PATH


class MockNotificationDaemon(ServiceInterface):
    """A silent notification sink that satisfies the freedesktop spec."""

    def __init__(self) -> None:
        super().__init__(INTERFACE_NAME)
        self._next_id = 1

    @method()
    def get_capabilities(self) -> "as":  # type: ignore[override]  # noqa: F722
        """Return supported capabilities."""
        return ["actions", "body"]

    @method()
    def get_server_information(self) -> "ssss":  # type: ignore[override]  # noqa: F722
        """Return server identity."""
        return ["terok-test", "terok-ai", "0.1", "1.2"]

    @method()
    def notify(  # noqa: PLR0913
        self,
        app_name: "s",  # noqa: F722
        replaces_id: "u",  # noqa: F722
        app_icon: "s",  # noqa: F722
        summary: "s",  # noqa: F722
        body: "s",  # noqa: F722
        actions: "as",  # noqa: F722
        hints: "a{sv}",  # noqa: F722
        expire_timeout: "i",  # noqa: F722
    ) -> "u":  # noqa: F722
        """Accept a notification and return an incrementing ID."""
        nid = self._next_id
        self._next_id += 1
        return nid

    @method()
    def close_notification(self, id: "u") -> None:  # noqa: A002, F722
        """Accept a close request (no-op)."""

    @signal()
    def action_invoked(self, id: "u", action_key: "s") -> "us":  # type: ignore[override]  # noqa: F722
        """Signal emitted when the user clicks an action button."""
        return [id, action_key]

    @signal()
    def notification_closed(self, id: "u", reason: "u") -> "uu":  # type: ignore[override]  # noqa: F722
        """Signal emitted when a notification is closed."""
        return [id, reason]


async def start_mock_daemon(bus_address: str) -> tuple[MessageBus, MockNotificationDaemon]:
    """Start the mock daemon on the given bus and request the well-known name.

    Returns:
        A ``(bus, daemon)`` tuple.  Call ``bus.disconnect()`` to tear down.
    """
    bus = await MessageBus(bus_address=bus_address).connect()
    daemon = MockNotificationDaemon()
    bus.export(OBJECT_PATH, daemon)
    await bus.request_name(BUS_NAME)
    return bus, daemon
