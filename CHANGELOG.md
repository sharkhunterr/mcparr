# Changelog

All notable changes to this project will be documented in this file. See [standard-version](https://github.com/conventional-changelog/standard-version) for commit guidelines.

### [0.2.1](https://github.com/sharkhunterr/mcparr/-/compare/v0.2.0...v0.2.1) (2025-12-30)


### Features

* add local development scripts ([0ed89bc](https://github.com/sharkhunterr/mcparr/-/commit/0ed89bc7aaee37f6b3a13fb494e5a61933c6d305))
* unified Docker image with backend + frontend ([65513d4](https://github.com/sharkhunterr/mcparr/-/commit/65513d40e489e19d07e47af8dfb34159e4acf819))


### Bug Fixes

* Docker Compose configuration for local development ([f3d241f](https://github.com/sharkhunterr/mcparr/-/commit/f3d241f390f9d489cadd25a31edb94d879747023))
* resolve CI build errors ([a794d99](https://github.com/sharkhunterr/mcparr/-/commit/a794d99e4f093789ef1d1389345c3f226f4ec3e9))

## [0.2.0](https://github.com/sharkhunterr/mcparr/-/compare/v0.1.15...v0.2.0) (2025-12-30)


### ⚠ BREAKING CHANGES

* Complete project restructure

- Add backend (Python/FastAPI) and frontend (React/Vite) in src/
- Centralize all Docker files in docker/ folder
- Update CI for Python backend tests and frontend build
- Remove old Node.js template files
- Add docker-compose for local development

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>

### Features

* migrate to MCParr AI Homelab Gateway ([0e44716](https://github.com/sharkhunterr/mcparr/-/commit/0e44716cdffdb40c156d366b1b6a912560d73766))

### [0.1.15](http://192.168.1.60/mcparr/mcparr/-/compare/v0.1.14...v0.1.15) (2025-12-30)

### [0.1.14](http://192.168.1.60/mcparr/mcparr/-/compare/v0.1.13...v0.1.14) (2025-12-30)

### [0.1.13](http://192.168.1.60/mcparr/mcparr/-/compare/v0.1.12...v0.1.13) (2025-12-30)

### [0.1.12](http://192.168.1.60/mcparr/mcparr/-/compare/v0.1.11...v0.1.12) (2025-12-30)

### [0.1.11](http://192.168.1.60/mcparr/mcparr/-/compare/v0.1.10...v0.1.11) (2025-12-30)

### [0.1.10](http://192.168.1.60/mcparr/mcparr/-/compare/v0.1.9...v0.1.10) (2025-12-30)

### [0.1.9](http://192.168.1.60/mcparr/mcparr/-/compare/v0.1.8...v0.1.9) (2025-12-30)


### Features

* ajout du deploy github ([16fee16](http://192.168.1.60/mcparr/mcparr/-/commit/16fee16eb17a0c2838f15e7d0159526931abddbe))

### [0.1.8](http://192.168.1.60/mcparr/mcparr/-/compare/v0.1.7...v0.1.8) (2025-12-30)

### [0.1.7](http://192.168.1.60/mcparr/mcparr/-/compare/v0.1.6...v0.1.7) (2025-12-30)

### [0.1.6](http://192.168.1.60/mcparr/mcparr/-/compare/v0.1.5...v0.1.6) (2025-12-30)

### [0.1.5](http://192.168.1.60/mcparr/mcparr/-/compare/v0.1.4...v0.1.5) (2025-12-23)

### [0.1.4](http://192.168.1.60/mcparr/mcparr/-/compare/v0.1.3...v0.1.4) (2025-12-23)

### [0.1.3](http://192.168.1.60/mcparr/mcparr/-/compare/v0.1.2...v0.1.3) (2025-12-22)

### [0.1.2](http://192.168.1.60/mcparr/mcparr/-/compare/v0.1.1...v0.1.2) (2025-12-22)

### [0.1.1](http://192.168.1.60/mcparr/mcparr/-/compare/v0.1.0...v0.1.1) (2025-12-22)

## 0.1.0 (2025-12-22)

### [0.1.5](http://192.168.1.60/root/template/-/compare/v0.1.4...v0.1.5) (2025-12-22)


### Features

* add release:deploy command for deployment ([384a8e5](http://192.168.1.60/root/template/-/commit/384a8e529356d61e2fc6050f23ed2a4856928d44))

### [0.1.4](http://192.168.1.60/root/template/-/compare/v0.1.3...v0.1.4) (2025-12-22)


### Features

* add link to full CHANGELOG in release notes ([411f7ed](http://192.168.1.60/root/template/-/commit/411f7ed74f1e5c74895f7b56ac3ce29d44021b7c))

### [0.1.3](http://192.168.1.60/root/template/-/compare/v0.1.2...v0.1.3) (2025-12-22)


### Bug Fixes

* use release-cli with changelog content ([7c845e5](http://192.168.1.60/root/template/-/commit/7c845e59e69fe8e97b96e124a71e5744be8af7a4))

### [0.1.2](http://192.168.1.60/root/template/-/compare/v0.1.1...v0.1.2) (2025-12-22)


### Bug Fixes

* use GitLab API to create release with changelog content ([df09597](http://192.168.1.60/root/template/-/commit/df095972b0663ea276e9e95aa51b65c2a8b92b54))

### [0.1.1](http://192.168.1.60/root/template/-/compare/v0.1.0...v0.1.1) (2025-12-22)


### Features

* extract release notes from CHANGELOG.md ([a8c7db9](http://192.168.1.60/root/template/-/commit/a8c7db9daaf25a0a91444ee633e3108e23c2fddc))

## 0.1.0 (2025-12-22)


### Features

* add ENABLE_GITLAB_REGISTRY variable to control publish ([b01f530](http://192.168.1.60/root/template/-/commit/b01f53042c935ac51b6e1f9f968a4241d3c73680))
* initial GitLab CI/CD template setup ([0a66e92](http://192.168.1.60/root/template/-/commit/0a66e92f4e77ec858769cf3a8248464002b1823a))


### Bug Fixes

* configure Docker-in-Docker without TLS ([e4e3a01](http://192.168.1.60/root/template/-/commit/e4e3a018bba5fe079cf87e29d1d4fb9317a55967))
* rename unused next parameter to _next for ESLint ([351adfb](http://192.168.1.60/root/template/-/commit/351adfb1b65c10e6dcff2ab1f11ef0bdd8439bce))
* use CI_PROJECT_NAME for docker image tag ([ab45119](http://192.168.1.60/root/template/-/commit/ab45119814553ef6d3ffa864f12c85bc82410dd6))
* use CI_PROJECT_PATH as fallback for DOCKER_IMAGE ([ecac3a7](http://192.168.1.60/root/template/-/commit/ecac3a772d96a15affc6ef2d7e6da2bd86b3dfa9))

## [1.0.0] - 2024-XX-XX

### ✨ Ajouts

- Version initiale du template
