"""Tests for output formatters."""

import json

import yaml

from k8s_investigate.formatters import format_results
from k8s_investigate.scanner import UnusedResource


def _sample_results():
    return [
        UnusedResource("default", "ConfigMap", "unused-cm", "Not used in any pod"),
        UnusedResource("default", "Secret", "old-secret", "Not used in any pod"),
        UnusedResource("kube-system", "Service", "orphan-svc", "No endpoints"),
        UnusedResource("", "PV", "old-pv", "Not bound"),
    ]


class TestJsonFormatter:
    def test_json_output(self):
        results = _sample_results()
        output = format_results(results, "json", show_reason=True)
        data = json.loads(output)
        assert "default" in data
        assert "(cluster-scoped)" in data
        assert len(data["default"]) == 2

    def test_json_without_reason(self):
        results = _sample_results()
        output = format_results(results, "json", show_reason=False)
        data = json.loads(output)
        for entries in data.values():
            for entry in entries:
                assert "reason" not in entry


class TestYamlFormatter:
    def test_yaml_output(self):
        results = _sample_results()
        output = format_results(results, "yaml", show_reason=True)
        data = yaml.safe_load(output)
        assert "default" in data


class TestTableFormatter:
    def test_table_output(self):
        results = _sample_results()
        output = format_results(results, "table", show_reason=False)
        assert "ConfigMap" in output
        assert "unused-cm" in output

    def test_table_empty(self):
        output = format_results([], "table")
        assert "No unused resources found" in output

    def test_table_group_by_resource(self):
        results = _sample_results()
        output = format_results(results, "table", group_by="resource")
        assert "ConfigMap" in output
