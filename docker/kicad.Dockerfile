# KiCad 10 toolchain for docs/schematics: kicad-cli (ERC/DRC/plots) and pcbnew Python. Notes: .claude/rules/dependencies.md
# Build: make kicad-image    Use: make erc | pcb-build | pcb-route | pcb-check | pcb-review | pcb-test
FROM kicad/kicad:10.0.8@sha256:3f4a01786dfbe803a65f345c3342b765db9add913f5e9448f8356793714ddc34
