# CHANGELOG


## v0.7.1 (2025-12-03)

### Bug Fixes

- Publish workflow dispatch not working
  ([`eb9cdca`](https://github.com/wpfleger96/claude-code-status-line/commit/eb9cdca65a42f449330e030e3e594180c1791808))


## v0.7.0 (2025-12-03)

### Chores

- Fix tracking for new sessions without any user messages yet
  ([`474e2e4`](https://github.com/wpfleger96/claude-code-status-line/commit/474e2e4c3ae9ad7be64980ac5e9db8f9153aeacf))

- Make sure we round consistently
  ([`018f76e`](https://github.com/wpfleger96/claude-code-status-line/commit/018f76e22612182f8e678dac42732b9f753babd6))

### Continuous Integration

- Add CI and publish workflows
  ([`3f0b403`](https://github.com/wpfleger96/claude-code-status-line/commit/3f0b403af6000ba2c2dd82d4431617acfbe2f7dd))

### Features

- Release on pypi
  ([`a7121b8`](https://github.com/wpfleger96/claude-code-status-line/commit/a7121b899d08792d8d5dd633f592e751b77109c0))


## v0.6.2 (2025-12-02)

### Bug Fixes

- Ansi colors
  ([`9903f4f`](https://github.com/wpfleger96/claude-code-status-line/commit/9903f4f46b1417d41dbb74d1e44e30cfc5ddcbd8))


## v0.6.1 (2025-12-02)

### Bug Fixes

- Don't render session prefix with ANSI code for contents
  ([`12dc915`](https://github.com/wpfleger96/claude-code-status-line/commit/12dc915f1c183301e452c2461b07de8b47ed1970))

### Chores

- Performance improvements and cleanup
  ([`43b2378`](https://github.com/wpfleger96/claude-code-status-line/commit/43b2378d0dad1e1c8d382fef780b073e3d686edb))


## v0.6.0 (2025-12-01)

### Chores

- Add pytest coverage
  ([`5eff626`](https://github.com/wpfleger96/claude-code-status-line/commit/5eff626fc86c1a737bb42eca40309e0b7d6a528d))

### Features

- Add customizable widget system with improved integrations and available widgets
  ([`060cf71`](https://github.com/wpfleger96/claude-code-status-line/commit/060cf718c911a2334e65d6b59f858ca7a6dd6099))

- Count tokens using real values in transcript files instead of our current estimated approach -
  Implement configurable widget system so that status line components and location are customizable
  - Add git integration to show working git status in status line - Add session clock metrics


## v0.5.0 (2025-11-26)


## v0.4.0 (2025-11-26)

### Chores

- Add proper testing suite
  ([`0409290`](https://github.com/wpfleger96/claude-code-status-line/commit/04092909355e733f7a685cfcb0a7b047e4596481))

### Features

- Release improved token counting
  ([`842eed1`](https://github.com/wpfleger96/claude-code-status-line/commit/842eed188721232ac7f9040bc89fc664b76ca017))

- Release improved token counting
  ([`cc4ded8`](https://github.com/wpfleger96/claude-code-status-line/commit/cc4ded80c0b3091a9391dfa7ac21f17d87792529))


## v0.3.1 (2025-11-25)

### Bug Fixes

- Get session ID from payload instead of filename to handle forked sessions correctly
  ([`ab2022c`](https://github.com/wpfleger96/claude-code-status-line/commit/ab2022c4c89f4a353a0aa050baf91e2a431c2915))


## v0.3.0 (2025-11-24)

### Features

- Add Opus 4.5 support and ensure we always display a human readable name instead of model ID
  ([`9e85d89`](https://github.com/wpfleger96/claude-code-status-line/commit/9e85d898144dd75dd224f870fca02ac85a11162a))


## v0.2.0 (2025-11-24)

### Features

- Show CC session ID in status line for easy debugging
  ([`81f27ad`](https://github.com/wpfleger96/claude-code-status-line/commit/81f27ad70acfcba361d57b6eecdfd10c7d65c6d0))


## v0.1.2 (2025-10-24)

### Bug Fixes

- Stop inflating token counts
  ([`95813ab`](https://github.com/wpfleger96/claude-code-status-line/commit/95813abec5b4b2100c362e44d7c7d1de283d38a1))


## v0.1.1 (2025-10-08)

### Bug Fixes

- 1m context models sometimes incorrectly showing 200K limit in statusline
  ([`7311a1a`](https://github.com/wpfleger96/claude-code-status-line/commit/7311a1ac2d49acbe9a8661233a82806790fb4ff1))


## v0.1.0 (2025-10-08)

### Features

- Initial release
  ([`d99b281`](https://github.com/wpfleger96/claude-code-status-line/commit/d99b281a89749393617212eb7a4eb1dfbc00ce27))


## v0.0.0 (2025-10-08)

### Continuous Integration

- Configure semantic release
  ([`a375d07`](https://github.com/wpfleger96/claude-code-status-line/commit/a375d07267423e28dbb4f5cac8b6d174c797e6eb))

- Fix package index
  ([`409e491`](https://github.com/wpfleger96/claude-code-status-line/commit/409e4914af12cd4a75b5d87635b8596e704c0704))

- Restructure project as proper Python package
  ([`ac41e95`](https://github.com/wpfleger96/claude-code-status-line/commit/ac41e95666c5eb4108118c7e9ad609f50dd19d94))
