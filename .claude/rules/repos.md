---
paths:
  - "ros2_ws/repos/**"
---

# ros2_ws/repos/

- `ros2_ws/repos/rccar.repos` is a vcstool manifest (`repositories:` name to type, url, version). Use: `vcs import src < ros2_ws/repos/rccar.repos`.
- `version` is a tag or a commit sha. Never a moving branch.
- Add only third-party sources that have no apt binary. Never our own code.
- Prefer rosdep and apt (`package.xml`) when a binary exists.
