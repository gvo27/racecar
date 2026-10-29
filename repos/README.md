# repos/

Third-party ROS sources built from source (no apt binary available). Never our own code.

Entry format in `rccar.repos`:

```yaml
repositories:
  <name>:
    type: git
    url: https://github.com/<org>/<repo>.git
    version: <tag-or-commit>   # pin a tag or commit, never a moving branch
```

Commands:

- `vcs import src < repos/rccar.repos` fetch the pinned sources
- `vcs pull src` update checkouts to the pinned versions
