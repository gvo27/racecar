# Lessons

Each lesson comes from an error on this project. Add a lesson when a check, a review or the owner finds an error that a rule could prevent.

1. A new Compound took the parts out of the model assembly, and the STEP file lost its part tree. The test of the label round trip found it. Rule: copy a part before you put it in a second Compound. (Phase A, 2026-11-27.)
2. The first hole finder read the bounding box of the face. It missed tilted holes and crashed on a face without a radius. Rule: read geometry from the surface definition, not from the bounding box. (Phase A review.)
3. The wall check measured a counterbore step as a wall. Rule: a check that compares faces must skip coaxial and adjacent faces, and each check needs a test of a correct shape that it must not flag. (Phase A review.)
4. The first iso picture used matplotlib 3D with one collection per part, and the depth order was wrong. Rule: look at each picture before you give it to the owner. (Phase A.)
