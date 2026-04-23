# SPDX-FileCopyrightText: 2026 Jiri Vyskocil
# SPDX-License-Identifier: Apache-2.0

"""Tests for :mod:`terok_clearance.client.podman_inspector`."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

from terok_clearance.client import podman_inspector as _pi
from terok_clearance.client.podman_inspector import PodmanInspector, _from_inspect
from terok_clearance.domain.container_info import ContainerInfo

_PODMAN = "/usr/bin/podman"


def _fake_inspect_result(*, returncode: int = 0, stdout: str = "[]", stderr: str = "") -> object:
    """Minimal ``subprocess.run`` stand-in."""
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class TestPodmanInspector:
    """End-to-end: id → ``subprocess.run`` stub → :class:`ContainerInfo`."""

    def test_empty_id_returns_empty_without_shelling_out(self) -> None:
        with patch.object(_pi.subprocess, "run") as run:
            info = PodmanInspector()("")
        assert info == ContainerInfo()
        run.assert_not_called()

    def test_podman_missing_returns_empty(self) -> None:
        with patch.object(_pi.shutil, "which", return_value=None):
            info = PodmanInspector()("abc123")
        assert info.container_id == ""

    def test_parsed_inspect_populates_fields(self) -> None:
        payload = json.dumps(
            [
                {
                    "Name": "/my-project-cli-k3v8h",
                    "State": {"Status": "running"},
                    "Config": {
                        "Annotations": {
                            "ai.terok.project": "my-project",
                            "ai.terok.task": "k3v8h",
                        }
                    },
                }
            ]
        )
        with (
            patch.object(_pi.shutil, "which", return_value=_PODMAN),
            patch.object(_pi.subprocess, "run", return_value=_fake_inspect_result(stdout=payload)),
        ):
            info = PodmanInspector()("my-project-cli-k3v8h")
        assert info.container_id == "my-project-cli-k3v8h"
        assert info.name == "my-project-cli-k3v8h"  # leading '/' stripped
        assert info.state == "running"
        assert info.annotations["ai.terok.project"] == "my-project"

    def test_nonzero_exit_soft_fails(self) -> None:
        with (
            patch.object(_pi.shutil, "which", return_value=_PODMAN),
            patch.object(
                _pi.subprocess,
                "run",
                return_value=_fake_inspect_result(returncode=125, stderr="no such container"),
            ),
        ):
            info = PodmanInspector()("missing")
        assert info == ContainerInfo()

    def test_timeout_soft_fails(self) -> None:
        with (
            patch.object(_pi.shutil, "which", return_value=_PODMAN),
            patch.object(
                _pi.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired(cmd="podman", timeout=5),
            ),
        ):
            info = PodmanInspector()("slow-host")
        assert info == ContainerInfo()

    def test_malformed_json_soft_fails(self) -> None:
        with (
            patch.object(_pi.shutil, "which", return_value=_PODMAN),
            patch.object(
                _pi.subprocess, "run", return_value=_fake_inspect_result(stdout="not-json")
            ),
        ):
            info = PodmanInspector()("whatever")
        assert info == ContainerInfo()

    def test_cache_returns_same_instance(self) -> None:
        payload = json.dumps([{"Name": "/container-1"}])
        with (
            patch.object(_pi.shutil, "which", return_value=_PODMAN),
            patch.object(
                _pi.subprocess, "run", return_value=_fake_inspect_result(stdout=payload)
            ) as run,
        ):
            inspector = PodmanInspector()
            first = inspector("container-1")
            second = inspector("container-1")
        assert first is second
        run.assert_called_once()

    def test_forget_drops_cache_entry(self) -> None:
        payload = json.dumps([{"Name": "/c"}])
        with (
            patch.object(_pi.shutil, "which", return_value=_PODMAN),
            patch.object(
                _pi.subprocess, "run", return_value=_fake_inspect_result(stdout=payload)
            ) as run,
        ):
            inspector = PodmanInspector()
            inspector("c")
            inspector.forget("c")
            inspector("c")
        assert run.call_count == 2


class TestFromInspect:
    """Hardening against podman returning unexpected JSON shapes."""

    def test_non_list_payload_returns_empty(self) -> None:
        assert _from_inspect("x", {"not": "a list"}) == ContainerInfo()

    def test_empty_list_returns_empty(self) -> None:
        assert _from_inspect("x", []) == ContainerInfo()

    def test_non_dict_element_returns_empty(self) -> None:
        assert _from_inspect("x", ["just a string"]) == ContainerInfo()

    def test_non_string_annotation_values_are_dropped(self) -> None:
        payload = [
            {
                "Name": "/c",
                "Config": {"Annotations": {"ok": "yes", "bogus": 42, "none": None}},
            }
        ]
        info = _from_inspect("c", payload)
        assert info.annotations == {"ok": "yes"}
