# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **PVC scanner**: PVCs owned by a `StatefulSet` are no longer incorrectly reported as unused when the StatefulSet is scaled down to 0 replicas. The scanner now checks `metadata.ownerReferences` and excludes any PVC whose owner is of kind `StatefulSet`, preventing false-positive reports that could lead to accidental data loss.

### Added

- Tests for `PVCScanner` covering: StatefulSet-owned PVCs excluded when no pods run, orphan PVCs still reported, PVCs owned by other controller kinds (e.g. `Job`) still checked, and StatefulSet-owned PVCs that are also mounted.

## [0.5.1] - 2025-01-01

### Added

- `CONTRIBUTING.md` with contribution guidelines.

## [0.5.0] - 2024-12-01

### Added

- Default resources excluded from scan by default.

## [0.4.0] - 2024-11-01

### Changed

- Version bump and minor updates.

## [0.3.0] - 2024-10-01

### Changed

- Pipeline updates.

## [0.2.0] - 2024-09-01

### Added

- Initial test coverage.

[Unreleased]: https://github.com/your-org/k8s-investigate/compare/v0.5.1...HEAD
[0.5.1]: https://github.com/your-org/k8s-investigate/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/your-org/k8s-investigate/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/your-org/k8s-investigate/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/your-org/k8s-investigate/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/your-org/k8s-investigate/releases/tag/v0.2.0
