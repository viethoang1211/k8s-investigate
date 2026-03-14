"""Tests for config module."""

from datetime import timedelta

import pytest

from k8s_purify.config import ScanOptions, parse_duration


class TestParseDuration:
    def test_hours(self):
        assert parse_duration("24h") == timedelta(hours=24)

    def test_days(self):
        assert parse_duration("7d") == timedelta(days=7)

    def test_minutes(self):
        assert parse_duration("30m") == timedelta(minutes=30)

    def test_combined(self):
        assert parse_duration("1d2h30m") == timedelta(days=1, hours=2, minutes=30)

    def test_seconds(self):
        assert parse_duration("90s") == timedelta(seconds=90)

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            parse_duration("")

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="invalid"):
            parse_duration("abc")


class TestScanOptions:
    def test_defaults(self):
        opts = ScanOptions()
        assert opts.output_format == "table"
        assert opts.group_by == "namespace"
        assert opts.delete is False
        assert opts.show_reason is False
        assert opts.namespaces == []
        assert opts.exclude_namespaces == []
