# Paw Map Modules

The paw map keeps animation ownership small so route playback can change
without affecting Memorial data or photo-sheet behavior.

## Dependency Direction

`PawMapView -> PawMapCanvas -> PawRoutePainter / PawMarker`

`PawMapMotion -> PawMapTimeline -> canvas and painter`

## Ownership

- `paw_map_motion.dart`: durations, curves, and visual motion constants.
- `paw_map_timeline.dart`: pure progress and position calculations.
- `paw_map_canvas.dart`: projected layout and animated-layer composition.
- `paw_route_painter.dart`: route drawing only.
- `paw_marker.dart`: marker appearance, semantics, and tap target only.
- `../paw_map_view.dart`: controller lifecycle, replay, reduced motion, and sheet
  coordination.

## Change Rules

- Add or tune motion values only in `PawMapMotion`.
- Keep timeline calculations deterministic and covered by unit tests.
- Do not open sheets or read providers from marker and painter modules.
- Keep route drawing inside `CustomPainter(repaint: animation)` to avoid
  rebuilding the full card on every frame.
- A marker remains tappable while the route is playing. Playback pauses while
  its photo sheet is open and resumes after dismissal.
- Reduced-motion mode must render the completed state without autoplay.
