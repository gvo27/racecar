---
paths:
  - "pcb/**"
  - "docs/pcb/**"
  - "docs/techctcarvera/**"
  - "ros2_ws/src/rccar_*/**"
---

# Domain plugins: enable on demand

`.claude/settings.json` (`enabledPlugins`) sets the plugins of a new session. Some domain plugins are off by default, because each enabled plugin loads its skills into each session. This rule tells you when to enable one.

| Folder | Plugin | Skills |
| --- | --- | --- |
| `pcb/**`, `docs/pcb/**`, `docs/techctcarvera/**` | `kicad-happy@kicad-happy` | kicad, spice, emc, datasheets, bom |
| `ros2_ws/src/rccar_*/**` | `ros2-engineering@ros2-engineering-skills` | ROS 2 and micro-ROS skills |

When you work on a file in a folder of the table:
1. Look for the skills of the plugin in your skill list. If they are there, do nothing more.
2. If they are not there, tell the user which plugin the folder needs. Ask the user to enable it for this session.
3. If the user agrees, run `claude plugin enable <plugin> --scope local`.
4. Tell the user to type `/reload-plugins`. You cannot type it.

Local scope writes `.claude/settings.local.json`. Git ignores that file, but it lasts across sessions. A local enable is for this session only: `make close` (target `plugins-reset`) removes all local enables, so the next session starts with the project default set. Do not change `enabledPlugins` in `.claude/settings.json` for one session.

To disable the plugin again, run `claude plugin disable <plugin> --scope local`, then `/reload-plugins`.

`claude-md-management@claude-plugins-official` is also off by default. It is not necessary to edit `CLAUDE.md`. Enable it the same way when the user asks for its commands. `plugin-dev@claude-plugins-official` (skill and agent review) is not in the project set: enable it the same way when the user asks for a skill or agent review.
