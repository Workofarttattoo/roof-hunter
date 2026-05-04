# Storm & roof damage — what to label (visual inspection)

Use **tight axis-aligned boxes** on **nadir or oblique aerial/roof photos** (drone, satellite, ladder POV). One class per box; overlapping signs get the **dominant** class or split boxes.

## Hail-dominant cues (class `hail_hit`)

- Random **pockmarks** / granular texture change vs neighbors (granule loss on asphalt).
- **Soft spots** or subtle depressions along **ridges, hip lines, valley metal** (metal may **dent**; shingles **bruise** without obvious missing tabs).
- **Collateral**: dented soft metals (vents, flashing, gutter backs) in same frame — box the **roof** damage, not distant cars.

## Wind-dominant cues (class `wind_uplift`)

- **Lifted tab edges**, **creased** shingle courses, **exposed nail lines** where seal is broken.
- **Corners** and **eaves** lifting first; **starter strip** pulls.

## Missing / stripped material (`shingle_loss`)

- Clear **void** where tab should be; **exposed underlayment** or **pattern break** in coursing.

## Ridge / penetration (`ridge_vent_damage`)

- **Cracked/displaced** ridge cap, **tilted cowl vents**, **split boots** around stacks.

## Metal (`metal_dent_crease`)

- Standing seam / R-panel **linear creases**, **quartering** hail dimples with directional shadow.

## Debris (`tree_debris_strike`)

- **Impact zone** under limb fall: **punctures**, **crushed** ridge, **localized displacement** (not “tree present in yard only”).

## Quality rules

- **Blur / heavy shadow**: skip or mark low confidence; don’t guess.
- **Pre-storm vs post**: train mostly **post-event** or label pair domain in a separate project.
- **Balance**: include **clean roof** patches only if you add class `healthy_roof` and teach background; otherwise the model learns from negatives implicitly.

Export to **YOLOv8** from Roboflow (or use native `labels/*.txt`). Point `training/dataset.yaml` at your folder.
