# Lessons

Each lesson comes from an error on this project. Add a lesson when a check, a review or the owner finds an error that a rule could prevent.

1. A new Compound took the parts out of the model assembly, and the STEP file lost its part tree. The test of the label round trip found it. Rule: copy a part before you put it in a second Compound. (Phase A, 2026-11-27.)
2. The first hole finder read the bounding box of the face. It missed tilted holes and crashed on a face without a radius. Rule: read geometry from the surface definition, not from the bounding box. (Phase A review.)
3. The wall check measured a counterbore step as a wall. Rule: a check that compares faces must skip coaxial and adjacent faces, and each check needs a test of a correct shape that it must not flag. (Phase A review.)
4. The first iso picture used matplotlib 3D with one collection per part, and the depth order was wrong. Rule: look at each picture before you give it to the owner. (Phase A.)
5. The post holes of the deck and the counterbores of the anchor had the same printed diameter (7.2 mm). A test that selected holes by diameter found 4 extra holes. Rule: in a model test, select the holes by part and by diameter. (Frame rev2, 2026-11-27.)
6. The iso picture of the anchor and the deck showed an empty deck slot: the painter drew the large deck faces over the small pin. Rule: do not use a picture as proof of a fit. Use a section or a distance check. (Frame rev2.)
