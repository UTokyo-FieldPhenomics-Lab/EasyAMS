# Batch Tools Remove Items Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a new `EasyAMS/Batch Tools/Remove Items` tool that deletes selected item types in selected chunks, with safe default states (all unchecked), confirmation before execution, and no auto-save.

**Architecture:** Rename module namespace from `batch_import` to `batch_tools` and migrate current batch tools into the new package. Add a new `remove_items.py` dialog using the same UI style as existing batch tools, but with the required control order: item types list -> tree control button row -> chunk/type tree -> action buttons. Deletion is type-based only: multi-instance types are removed entirely per selected chunk. EasyAMS ships a built-in API capability matrix in Python (`dict`, based on API survey), then performs local sync/probe on first run per Metashape version; unsupported item types are disabled in UI.

**Tech Stack:** Python 3.9+, PySide2, Metashape API, pytest (`uv run pytest`)

---

### Task 1: Create package migration skeleton (`batch_import` -> `batch_tools`)

**Files:**
- Create: `src/easyams/batch_tools/__init__.py`
- Create: `src/easyams/batch_tools/images.py`
- Create: `src/easyams/batch_tools/masks.py`
- Create: `src/easyams/batch_tools/markers.py`
- Modify: `src/easyams/__init__.py`
- Optional compatibility shim: `src/easyams/batch_import/__init__.py`

**Step 1: Write the failing import test**

```python
def test_batch_tools_package_importable():
    import easyams as ams

    assert hasattr(ams, "batch_tools")
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_batch_tools_remove_items.py::test_batch_tools_package_importable -v`
Expected: FAIL because `batch_tools` package does not exist yet.

**Step 3: Add package and wire root import**

```python
# src/easyams/batch_tools/__init__.py
from . import images
from . import masks
from . import markers
```

```python
# src/easyams/__init__.py (import section)
from . import (
    sahi_onnx,
    batch_tools,
    ui,
    utils,
    web_api,
    gcp,
    updator,
)
```

**Step 4: Update menu callback references**

```python
Metashape.app.addMenuItem(
    "EasyAMS/Batch Tools/Import RGB Images",
    batch_tools.images.create_batch_image_importer,
)
```

Apply the same change for masks and markers menu entries.

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_batch_tools_remove_items.py::test_batch_tools_package_importable -v`
Expected: PASS.

**Step 6: Commit**

```bash
git add src/easyams/__init__.py src/easyams/batch_tools src/easyams/batch_import/__init__.py tests/test_batch_tools_remove_items.py
git commit -m "refactor: migrate batch tools namespace from batch_import to batch_tools"
```

### Task 2: Add Remove Items dialog skeleton with required layout and defaults

**Files:**
- Create: `src/easyams/batch_tools/remove_items.py`
- Modify: `src/easyams/batch_tools/__init__.py`
- Modify: `src/easyams/__init__.py`
- Test: `tests/test_batch_tools_remove_items.py`

**Step 1: Write failing UI structure test**

```python
def test_remove_items_dialog_defaults_unchecked(qtbot, monkeypatch):
    dlg = BatchRemoveItemsDialog(parent=None)

    assert dlg.item_list.count() > 0
    assert dlg.get_selected_item_types() == []
    assert dlg.get_selected_chunk_keys() == []


def test_unsupported_item_types_are_disabled_by_version(qtbot, monkeypatch):
    monkeypatch.setattr("easyams.batch_tools.remove_items.get_metashape_version", lambda: "2.1.2")
    dlg = BatchRemoveItemsDialog(parent=None)

    assert dlg.is_item_type_enabled("Depth Maps") is False
    assert dlg.is_item_type_enabled("Point Clouds") is False
    assert dlg.is_item_type_enabled("Models") is False
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_batch_tools_remove_items.py::test_remove_items_dialog_defaults_unchecked -v`
Expected: FAIL because dialog does not exist yet.

**Step 3: Implement minimal dialog shell**

```python
class BatchRemoveItemsDialog(QDialog):
    """Dialog for removing selected item types in selected chunks."""

    ITEM_TYPES = (
        "Cameras",
        "Masks",
        "Markers",
        "Thumbnails",
        "Scale Bars"
        "Shapes",
        "Depth Maps",
        "Point Clouds",
        "Laser Scans"
        "Models",
        "Textures",
        "Tiled Models",
        "Elevation Models",
        "Orthomosaics",
        ... # and more api supported
    )
```

Add widgets in this exact order:
1. Item types list (`QListWidget`, multi-select, default no selection)
2. Tree control buttons (`Expand`, `Collapse`, `Select All`, `Clear`)
3. File tree (`Chunks -> Type nodes`)
4. Bottom action buttons (`Cancel`, `Execute`)

After populating the unique type list, call a capability resolver based on current Metashape version and apply disabled state to unsupported types. Resolver data source must come from the capability matrix sync workflow (Task 3), not hard-coded booleans.

Capability baseline for planning:
- `Depth Maps`, `Point Clouds`, `Models`, `Tiled Models`, `Elevation Models`, `Orthomosaics`: enable only for `>=2.1.3`
- `Scale Bars`, `Cameras`, `Markers`: available in old versions
- `Masks`, `Thumbnails`, `Laser Scans`, `Textures`, `Tie Points`: do not map to `Chunk.remove(items)` and must remain disabled unless dedicated deletion API is implemented in a later task.

**Step 4: Register new menu entry**

```python
Metashape.app.addMenuItem(
    "EasyAMS/Batch Tools/Remove Items",
    batch_tools.remove_items.create_batch_remove_items,
)
```

**Step 5: Run targeted tests**

Run: `uv run pytest tests/test_batch_tools_remove_items.py -k defaults -v`
Expected: PASS for default-selection behavior.

**Step 6: Commit**

```bash
git add src/easyams/batch_tools/remove_items.py src/easyams/batch_tools/__init__.py src/easyams/__init__.py tests/test_batch_tools_remove_items.py
git commit -m "feat: add remove items dialog skeleton with safe defaults"
```

### Task 3: Add capability matrix config and first-run sync workflow

**Files:**
- Create: `src/easyams/api_capability.py`
- Modify: `src/easyams/batch_tools/remove_items.py`
- Test: `tests/test_batch_tools_remove_items.py`

**Step 1: Write failing matrix loading and sync tests**

```python
def test_loads_builtin_api_capability():
    matrix = load_api_capability()

    assert "versions" in matrix
    assert "2.2.1" in matrix["versions"]


def test_runs_local_probe_when_current_version_not_synced(monkeypatch):
    monkeypatch.setattr("easyams.api_capability.get_metashape_version", lambda: "2.2.1")
    monkeypatch.setattr("easyams.api_capability.read_runtime_sync_state", lambda: {"2.2.1": {"synced": False}})

    called = {"probe": 0}

    def _probe(version, base_caps):
        called["probe"] += 1
        return base_caps

    monkeypatch.setattr("easyams.api_capability.probe_api_capabilities", _probe)
    resolve_capabilities_for_current_version()

    assert called["probe"] == 1


def test_unknown_new_version_clones_nearest_then_probes(monkeypatch):
    monkeypatch.setattr("easyams.api_capability.get_metashape_version", lambda: "2.3.0")
    caps = resolve_capabilities_for_current_version()

    assert caps["_source_version"] == "2.2.1"
    assert caps["_probed"] is True
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_batch_tools_remove_items.py -k "capability_matrix or synced or unknown_new_version" -v`
Expected: FAIL because matrix module and runtime sync logic do not exist yet.

**Step 3: Add built-in capability matrix Python dict**

Add a version-indexed baseline matrix in `easyams/api_capability.py` using plain Python constants (no JSON download/update dependency at install time). Include metadata keys:
- `SCHEMA_VERSION`
- `GENERATED_FROM`
- `REMOVE_ITEMS_CAPABILITY_BY_VERSION`

Per-version value structure example:

```python
REMOVE_ITEMS_CAPABILITY_BY_VERSION = {
    "2.2.1": {
        "supports": {
            "Cameras": True,
            "Masks": False,
            "Markers": True,
            "Thumbnails": False,
            "Scale Bars": True,
            "Shapes": False,
            "Depth Maps": True,
        },
    },
}
```

**Step 4: Implement runtime sync strategy**

In `easyams/api_capability.py`:
- Load built-in matrix from Python constants (`easyams/api_capability.py`).
- Keep runtime sync state in EasyAMS cache config file (via existing config manager), not in package source files.
- On dialog startup, resolve current version capabilities:
  - If current version exists and `synced=true`, use runtime cached result.
  - If current version exists but `synced!=true`, run API probe and update runtime cache (`synced=true`).
  - If current version is newer and not included, clone nearest lower known version as baseline, run API probe, then store as new runtime version entry with `synced=true`.

**Step 5: Wire resolver into dialog enable/disable logic**

In `remove_items.py`, replace hard-coded version checks with `resolve_capabilities_for_current_version()` output.

**Step 6: Run targeted tests**

Run: `uv run pytest tests/test_batch_tools_remove_items.py -k "api_capability or defaults" -v`
Expected: PASS.

**Step 7: Commit**

```bash
git add src/easyams/api_capability.py src/easyams/batch_tools/remove_items.py tests/test_batch_tools_remove_items.py
git commit -m "feat: add capability matrix sync workflow for remove items"
```

### Task 4: Build chunk/type preview model with count labels

**Files:**
- Modify: `src/easyams/batch_tools/remove_items.py`
- Test: `tests/test_batch_tools_remove_items.py`

**Step 1: Write failing preview label test**

```python
def test_preview_labels_follow_type_count_format(monkeypatch):
    preview = build_preview_for_chunk(fake_chunk)

    assert "Markers (6)" in preview
    assert "Tie Points (1)" in preview
    assert "Dense Cloud (3)" in preview
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_batch_tools_remove_items.py::test_preview_labels_follow_type_count_format -v`
Expected: FAIL.

**Step 3: Implement count collector and tree binding**

```python
def get_chunk_type_counts(chunk):
    """Collect type-based counts for one chunk."""
    return {
        "Markers": len(chunk.markers),
        "Cameras": len(chunk.cameras),
        "Shapes": len(chunk.shapes) if hasattr(chunk, "shapes") else 0,
        "Tie Points": 1 if getattr(chunk, "tie_points", None) else 0,
    }
```

Render each subitem with `Type (count)` format only (type-based delete mode).

**Step 4: Update preview refresh trigger**

When user changes selected item types or chunk checks, refresh tree labels immediately.

**Step 5: Run targeted tests**

Run: `uv run pytest tests/test_batch_tools_remove_items.py -k preview -v`
Expected: PASS.

**Step 6: Commit**

```bash
git add src/easyams/batch_tools/remove_items.py tests/test_batch_tools_remove_items.py
git commit -m "feat: add type-count preview for remove items tree"
```

### Task 5: Implement type-based deletion handlers (including camera groups)

**Files:**
- Modify: `src/easyams/batch_tools/remove_items.py`
- Test: `tests/test_batch_tools_remove_items.py`

**Step 1: Write failing deletion behavior tests**

```python
def test_delete_cameras_also_removes_groups(fake_chunk):
    apply_type_deletion(fake_chunk, ["Cameras (+Groups)"])

    assert len(fake_chunk.cameras) == 0
    assert len(fake_chunk.camera_groups) == 0
```

```python
def test_delete_heavy_assets_type_based(fake_chunk):
    apply_type_deletion(fake_chunk, ["Model", "DSM", "DOM"])

    assert fake_chunk.model is None
    assert fake_chunk.elevation is None
    assert fake_chunk.orthomosaic is None
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_batch_tools_remove_items.py -k deletion -v`
Expected: FAIL.

**Step 3: Implement handler map with Metashape-version guards**

Use a dictionary mapping item type to deletion function. Each function should:
- Handle only one responsibility
- Use guard clauses for missing attributes
- Keep under 50 lines

Only register deletion handlers for types supported by current API version. Unsupported types remain disabled in UI and are excluded from execution set.

Deletion scope:
- `Markers`: remove all markers in chunk
- `Cameras`: remove all cameras and then all camera groups
- `Shapes`: clear all shapes
- `Tie Points`: clear tie points object/reference
- `Dense Cloud`: clear dense cloud object/reference
- `Point Cloud`: clear point cloud object/reference
- `Model`: clear model object/reference
- `DSM`: clear elevation object/reference
- `DOM`: clear orthomosaic object/reference
- and more in ITEM_TYPES

**Step 4: Add execution confirmation dialog**

Before deletion, show selected chunk count, selected type list, and total impacted nodes. Continue only on explicit confirm.

**Step 5: Run targeted tests**

Run: `uv run pytest tests/test_batch_tools_remove_items.py -k "deletion or confirm" -v`
Expected: PASS.

**Step 6: Commit**

```bash
git add src/easyams/batch_tools/remove_items.py tests/test_batch_tools_remove_items.py
git commit -m "feat: implement type-based chunk item deletion with confirmation"
```

### Task 6: Final verification and no-auto-save guarantee

**Files:**
- Modify: `src/easyams/batch_tools/remove_items.py`
- Test: `tests/test_batch_tools_remove_items.py`

**Step 1: Write failing no-save test**

```python
def test_execute_does_not_call_document_save(monkeypatch):
    called = {"save": 0}

    def fake_save():
        called["save"] += 1

    monkeypatch.setattr(fake_doc, "save", fake_save)
    dlg.execute_remove()

    assert called["save"] == 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_batch_tools_remove_items.py::test_execute_does_not_call_document_save -v`
Expected: FAIL.

**Step 3: Ensure execution path never calls `doc.save()`**

Keep deletion operation in-memory only, then refresh UI and show result dialog.

**Step 4: Run full tests for this feature**

Run: `uv run pytest tests/test_batch_tools_remove_items.py -v`
Expected: PASS.

**Step 5: Run project regression suite**

Run: `uv run pytest -v`
Expected: Existing tests and new tests pass.

**Step 6: Commit**

```bash
git add src/easyams/batch_tools/remove_items.py tests/test_batch_tools_remove_items.py
git commit -m "test: verify remove items flow and no-auto-save behavior"
```

### Task 7: Cleanup and namespace completion

**Files:**
- Optional modify: `src/easyams/batch_import/__init__.py`
- Review: all imports in `src/easyams/**/*.py`

**Step 1: Search for stale `batch_import` references**

Run: `uv run python -m pip --version` (venv sanity)
Run: `rg "batch_import" src tests`
Expected: no active runtime imports except optional compatibility shim.

**Step 2: Keep or remove compatibility shim intentionally**

If backward compatibility is needed, keep shim re-exporting `batch_tools`.
If not needed, remove shim and update all references.

**Step 3: Run final full tests again**

Run: `uv run pytest -v`
Expected: PASS.

**Step 4: Final commit**

```bash
git add src/easyams
git add tests/test_batch_tools_remove_items.py
git commit -m "refactor: finalize batch tools namespace and remove items integration"
```
