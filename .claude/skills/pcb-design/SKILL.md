---
name: pcb-design
description: Use when you design or change a KiCad schematic or board in pcb/ - a new board, a new part, a net, a footprint, placement, routing, zones, a board tool or check - and before a claim that a schematic or a board is correct, complete or ready for review. Gives the workflow (intake, plan, schematic, board, independent review, report), the check matrix, the kicad-happy analyzers and the lessons list. Keywords - KiCad, schematic, PCB, ERC, DRC, EMC, power budget, design review, kicad-happy.
---

# PCB design

The main session implements. The agent `pcb-reviewer` reviews with a fresh context after each phase. The owner approves the plan and the schematic. This follows the user-scope engineering workflow: implement, verify, independent review, fix, report.

Project rules: `.claude/rules/schematics.md`. Board context: `docs/pcb/`. Lab facts: the lab directory (`lab:` in `.claude/CLAUDE.md`).

## References (read when the step starts)
| File | Use |
| --- | --- |
| `references/intake.md` | Start questions, the plan (gate 1), the environment check |
| `references/board-loop.md` | Work rules, the checks after each edit, the schematic and board loops |
| `references/check-matrix.md` | All checks, their pass conditions, what each one cannot find, triage, design principles |
| `references/kicad-happy.md` | Which kicad-happy analyzer in which phase, how to run a script, findings are claims |
| `references/lessons.md` | Lessons from errors on this project. Read before a design step and before a review |

## Skills
| Skill | When |
| --- | --- |
| kicad-happy `kicad`, `emc` | each review of a schematic or a board (`make pcb-gate`), and to read a rule id |
| kicad-happy `spice` | subcircuit checks, only with `ngspice` |
| kicad-happy `datasheets`, `lcsc` | through skill `hw-research` |
| `pcb-parts` | part choice, BOM fields, compatibility of parts, connectors and harnesses |
| `pcb-lab-config` | read or change a lab fact (machine, bits, stock, rivets, limits) |
| `pcb-milling-check` | a board for the lab mill |
| `pcb-fab` | "Is this board ready to order or to mill?", fab outputs, supplier files |
| kicad-happy `jlcpcb`, `pcbway` | method "fab house": the fab rules and limits of that house. No project skill covers fab-house rule compliance: tell the owner about the gap |

## Step 0
1. Check that the kicad-happy skills are in your skill list. If not, follow `.claude/rules/plugins.md` (the owner enables the plugin for the session). If they are still missing, stop and tell the owner. Do not replace the analyzers with your own reading of the files.
2. Run the environment check of `references/intake.md`.

## Workflow
1. **Intake and plan** (`references/intake.md`). Owner gate 1: the plan.
2. **Schematic loop** (`references/board-loop.md`). Run the schematic rows of the check matrix after each task.
3. **Review the schematic.** Dispatch `pcb-reviewer` with the scope "schematic", the plan path and the commit range. Fix each blocker and major finding in this session, run the checks again, and dispatch the reviewer again. Owner gate 2: the schematic.
4. **Board loop** (`references/board-loop.md`). Run the board rows after each change. Method "mill" adds `pcb-milling-check`.
5. **Review the board.** Run `make pcb-gate` first. Dispatch `pcb-reviewer` with the scope "board" and the gate output directory. Repeat until no blocker and no major finding is open.
6. **Fab outputs** (skill `pcb-fab`).
7. **Report** (below). Set the plan status to `done`.

## Rules
- Evidence before each claim. A check result counts only with its output from this session. Words such as "millable", "fits" and "within rating" need a check or a measurement.
- A limit is `confirmed` or `assumed`, with a source. Never change a limit, a check or a waiver to make a board pass.
- The schematic is the source for the board.
- An analyzer finding is a claim. Give it a verdict (`references/check-matrix.md`, Triage).
- Never run hardware tests. Bench checks are owner steps.
- Do not review your own work as the only review. Dispatch `pcb-reviewer`.
- The active board is `pcb/src` (the next release, rev3). Work on it and review only it, unless the owner names another board. Releases in `pcb/releases/` are frozen: never change or review them again. Review records: `docs/pcb/releases/<rev>/review/README.md`, latest state only.
- Stay in the task scope. Write other problems in the report. Do not fix them without the owner.
- Do not push and do not open a PR unless the owner asks.
- Text for docs, commits and PRs follows `.claude/rules/writing.md`.

## Report
Report to the owner only when no finding is open, in this order:
1. Owner feedback necessary: each `assumed` limit and each `TBD` part value that changes a result.
2. Check table: command, result, the count of errors and warnings. Copy the numbers from the output of this run.
3. Findings fixed in the loop, one line each, with the commit.
4. Open questions and owner steps (GUI checks, bench checks, lab tech questions).
5. What was not checked, and why.
