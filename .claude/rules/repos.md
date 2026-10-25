---
paths:
  - "repos/**"
---

# repos/

- `repos/rccar.repos` = vcstool manifest; `repositories:` map of name -> {type, url, version}.
- `version` = tag or commit sha. Never a moving branch.
- Add only third-party sources with no apt binary. Never our own code.
- Use: `vcs import src < repos/rccar.repos`; `vcs pull src`.
- Prefer rosdep/apt (`package.xml`) when a binary exists.
