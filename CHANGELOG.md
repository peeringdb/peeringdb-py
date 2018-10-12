
# peeringdb-py change log


## [Unreleased]
### Added
### Fixed
### Changed
### Deprecated
### Removed
### Security


## [0.6.1] 2018-10-12
### Fixed
- don't use pip.main, instead lauch a subprocess


## [0.6.0]
### Fixed
- pinned dependencies version


## [0.5.1]
### Added
- separate sync tests
### Fixed
- output whois in utf8, fixed #15
- django requirements


## [0.5.0]
### Added
- sync_only config option
### Fixed
- field name for info_prefixe4 in whois format
### Changed
- updated deps


## [0.4.4]
### Added
- CHANGELOG!
- whois command
- conf_dump command
- drop_tables command
- depth to get command
- lookup net by asn, ixnets to client

### Fixed
- get/whois commands honor --config
- fix #2, pass through settings to db
