# Remove Items Capability Matrix Report

## Scope

- Source PDFs: `/home/crest/d/OneDrive/Program/GitHub/EasyAMS/tests/pdfs/metashape_python_api_*.pdf`
- Versions checked: `1.5.0` -> `2.2.1`
- Main API checked: `Chunk.remove(items)`
- Extra APIs checked for non-Chunk.remove types:
  - shape layer: `remove(items)` for `Shape/ShapeGroup`
  - model: `remove(items)` for `Model.Texture`

## Key Findings

- `Chunk.remove(items)` exists in all checked versions, but supported item classes expanded over time.
- Milestones:
  - `1.5.0`: base classes (camera/marker/scalebar related)
  - `1.5.2`: adds `CameraTrack`
  - `2.1.3`: adds heavy assets (`DepthMaps`, `PointCloud`, `Model`, `TiledModel`, `Elevation`, `Orthomosaic`, groups)
  - `2.2.x`: adds `Component`

## Item-Type Capability Matrix (for EasyAMS Remove Items UI)

Legend: `chunk.remove` = directly supported by `Chunk.remove(items)`; `special` = has separate remove API; `no` = no direct remove API confirmed in this pass.

| Item Type | 1.5.0-2.1.2 | 2.1.3-2.2.1 | Notes |
|---|---:|---:|---|
| Cameras | yes | yes | via `Camera` + `CameraGroup` |
| Masks | no | no | generation/import APIs exist, no direct remove confirmed |
| Markers | yes | yes | via `Marker` (+ `MarkerGroup`) |
| Thumbnails | no | no | thumbnail object exists, not in `Chunk.remove` list |
| Scale Bars | yes | yes | via `Scalebar` + `ScalebarGroup` |
| Shapes | special | special | remove from shape layer (`Shape`/`ShapeGroup`) |
| Depth Maps | no | yes | `Chunk.remove` support appears in `2.1.3+` |
| Point Clouds | no | yes | `PointCloud`/`PointCloudGroup` in `2.1.3+` |
| Laser Scans | no | no | no direct remove in `Chunk.remove` list |
| Models | no | yes | `Model`/`ModelGroup` in `2.1.3+` |
| Textures | special | special | via `Model.remove(list[Model.Texture])` |
| Tiled Models | no | yes | `TiledModel` in `2.1.3+` |
| Elevation Models | no | yes | `Elevation` in `2.1.3+` |
| Orthomosaics | no | yes | `Orthomosaic` in `2.1.3+` |
| Tie Points | no | no | clean/thin APIs exist; no direct `remove(item)` confirmed |

## Latest API Reference Snapshot (2.2.1)

`Chunk.remove(items)` supports these classes:

- `Metashape.Chunk`
- `Metashape.Sensor`
- `Metashape.Component`
- `Metashape.CameraGroup`
- `Metashape.MarkerGroup`
- `Metashape.ScalebarGroup`
- `Metashape.Camera`
- `Metashape.Marker`
- `Metashape.Scalebar`
- `Metashape.CameraTrack`
- `Metashape.DepthMaps`
- `Metashape.PointCloud`
- `Metashape.PointCloudGroup`
- `Metashape.Model`
- `Metashape.ModelGroup`
- `Metashape.TiledModel`
- `Metashape.Elevation`
- `Metashape.Orthomosaic`
- `Metashape.Trajectory`

## Proposed Baseline for Built-in Matrix

- Default baseline version for heavy assets: `2.1.3`
- If runtime Metashape version not included:
  - copy nearest lower version capability row,
  - run local API probe,
  - persist runtime synced result.
