# Changelog


## Unreleased


## 1.4.0
### Added
- support for Carrier and CarrierFacility


## 1.3.0
### Added
- api key support added (#62)
- python 3.10
### Fixed
- pyyaml dependency missing (#57)
### Removed
- python 3.6


## 1.2.1
### Fixed
- fix peeringdb command not found error


## 1.2.0
### Added
- poetry package management
- python3.9 support
### Fixed
- linting pass
### Removed
- python3.5 support


## 1.1.0
### Added
- add py3.7 to tox and travis tests
### Fixed
- fixed sync issues with django-peeringdb and django3 (peeringdb/django-peeringdb#37)
- fixed sync issues with django-peeringdb and mysql (#41)
- better data for tests (#40)
### Removed
- remove py2.7 support (#37)
- remove py3.4 tests (py3.4 EOL reached)


## 1.0.0
### Changed
- client refactor


## 0.6.1
### Fixed
- don't use pip.main, instead lauch a subprocess


## 0.6.0
### Fixed
- pinned dependencies version


## 0.5.1
### Added
- separate sync tests
### Fixed
- output whois in utf8, fixed #15
- django requirements


## 0.5.0
### Added
- sync_only config option
### Fixed
- field name for info_prefixe4 in whois format
### Changed
- updated deps


## 0.4.4
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