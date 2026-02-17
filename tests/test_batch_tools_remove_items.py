import os
import types

from PySide2.QtCore import Qt
from PySide2.QtWidgets import QApplication


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _get_qapp():
    """Return an available Qt application instance for widget tests."""
    app = QApplication.instance()
    if app:
        return app
    return QApplication([])


def test_batch_tools_package_importable():
    import easyams as ams

    assert hasattr(ams, "batch_tools")


def test_remove_items_dialog_defaults_unchecked(monkeypatch):
    from easyams.batch_tools.remove_items import BatchRemoveItemsDialog

    monkeypatch.setattr(
        "easyams.batch_tools.remove_items.resolve_dialog_capabilities",
        lambda: {"Cameras": True, "Markers": True, "Scale Bars": True},
    )
    _get_qapp()
    dialog = BatchRemoveItemsDialog(parent=None)

    assert dialog.item_list.count() > 0
    assert dialog.get_selected_item_types() == []
    assert dialog.get_selected_chunk_keys() == []


def test_unsupported_item_types_are_disabled_by_version(monkeypatch):
    from easyams.batch_tools.remove_items import BatchRemoveItemsDialog

    monkeypatch.setattr(
        "easyams.batch_tools.remove_items.get_metashape_version",
        lambda: "2.1.2",
    )
    monkeypatch.setattr(
        "easyams.batch_tools.remove_items.resolve_dialog_capabilities",
        lambda: {
            "Cameras": True,
            "Markers": True,
            "Scale Bars": True,
            "Depth Maps": False,
            "Point Clouds": False,
            "Models": False,
        },
    )
    _get_qapp()
    dialog = BatchRemoveItemsDialog(parent=None)

    assert dialog.is_item_type_enabled("Depth Maps") is False
    assert dialog.is_item_type_enabled("Point Clouds") is False
    assert dialog.is_item_type_enabled("Models") is False


def test_loads_builtin_api_capability():
    from easyams.api_capability import load_api_capability

    matrix = load_api_capability()

    assert "versions" in matrix
    assert "2.2.1" in matrix["versions"]


def test_runs_local_probe_when_current_version_not_synced(monkeypatch):
    from easyams.api_capability import resolve_capabilities_for_current_version

    monkeypatch.setattr(
        "easyams.api_capability.get_metashape_version",
        lambda: "2.2.1",
    )
    monkeypatch.setattr(
        "easyams.api_capability.read_runtime_sync_state",
        lambda: {"2.2.1": {"synced": False}},
    )
    monkeypatch.setattr(
        "easyams.api_capability.write_runtime_sync_state",
        lambda _state: None,
    )

    called = {"probe": 0}

    def _probe(_version, base_caps):
        called["probe"] += 1
        return base_caps

    monkeypatch.setattr("easyams.api_capability.probe_api_capabilities", _probe)
    resolve_capabilities_for_current_version()

    assert called["probe"] == 1


def test_unknown_new_version_clones_nearest_then_probes(monkeypatch):
    from easyams.api_capability import resolve_capabilities_for_current_version

    monkeypatch.setattr(
        "easyams.api_capability.get_metashape_version",
        lambda: "2.3.0",
    )
    monkeypatch.setattr(
        "easyams.api_capability.read_runtime_sync_state",
        lambda: {},
    )
    monkeypatch.setattr(
        "easyams.api_capability.write_runtime_sync_state",
        lambda _state: None,
    )
    caps = resolve_capabilities_for_current_version()

    assert caps["_source_version"] == "2.2.1"
    assert caps["_probed"] is True


def test_batch_import_shim_not_recursive():
    from easyams import batch_import
    from easyams import batch_tools

    assert batch_import.images is not batch_tools.images


def test_remove_items_only_shows_existing_types(monkeypatch):
    from easyams.batch_tools.remove_items import BatchRemoveItemsDialog

    class _Chunk:
        def __init__(self, key, label):
            self.key = key
            self.label = label
            self.cameras = [1]
            self.markers = [1, 2]
            self.scalebars = []
            self.shapes = []
            self.depth_maps = None
            self.point_cloud = None
            self.model = None
            self.tiled_model = None
            self.elevation = None
            self.orthomosaic = None
            self.tie_points = None

    fake_doc = types.SimpleNamespace(chunks=[_Chunk(1, "Chunk A")])
    fake_app = types.SimpleNamespace(document=fake_doc)

    monkeypatch.setattr(
        "easyams.batch_tools.remove_items.Metashape",
        types.SimpleNamespace(app=fake_app),
    )
    monkeypatch.setattr(
        "easyams.batch_tools.remove_items.resolve_dialog_capabilities",
        lambda: {"Cameras": True, "Markers": True},
    )

    _get_qapp()
    dialog = BatchRemoveItemsDialog(parent=None)
    item_names = [
        dialog.item_list.item(index).text() for index in range(dialog.item_list.count())
    ]

    assert item_names == ["Cameras", "Markers"]


def test_chunk_tree_only_shows_chunk_existing_types(monkeypatch):
    from easyams.batch_tools.remove_items import BatchRemoveItemsDialog

    class _Chunk:
        def __init__(self, key, label, has_model):
            self.key = key
            self.label = label
            self.cameras = [1]
            self.markers = []
            self.scalebars = []
            self.shapes = []
            self.depth_maps = None
            self.point_cloud = None
            self.model = object() if has_model else None
            self.tiled_model = None
            self.elevation = None
            self.orthomosaic = None
            self.tie_points = None

    chunks = [_Chunk(1, "Chunk A", False), _Chunk(2, "Chunk B", True)]
    fake_doc = types.SimpleNamespace(chunks=chunks)
    fake_app = types.SimpleNamespace(document=fake_doc)

    monkeypatch.setattr(
        "easyams.batch_tools.remove_items.Metashape",
        types.SimpleNamespace(app=fake_app),
    )
    monkeypatch.setattr(
        "easyams.batch_tools.remove_items.resolve_dialog_capabilities",
        lambda: {"Cameras": True, "Models": True},
    )

    _get_qapp()
    dialog = BatchRemoveItemsDialog(parent=None)

    root = dialog.tree_widget.invisibleRootItem()
    first_chunk = root.child(0)
    second_chunk = root.child(1)
    first_children = [
        first_chunk.child(i).text(0) for i in range(first_chunk.childCount())
    ]
    second_children = [
        second_chunk.child(i).text(0) for i in range(second_chunk.childCount())
    ]

    assert first_children == ["Cameras (1)"]
    assert second_children == ["Cameras (1)", "Models (1)"]


def test_preview_updates_to_red_strike_for_selected_deletions(monkeypatch):
    from easyams.batch_tools.remove_items import BatchRemoveItemsDialog

    class _Chunk:
        def __init__(self):
            self.key = 1
            self.label = "Chunk A"
            self.cameras = [1]
            self.markers = [1]
            self.scalebars = []
            self.shapes = []
            self.depth_maps = None
            self.point_cloud = None
            self.model = None
            self.tiled_model = None
            self.elevation = None
            self.orthomosaic = None
            self.tie_points = None

    fake_doc = types.SimpleNamespace(chunks=[_Chunk()])
    fake_app = types.SimpleNamespace(document=fake_doc)

    monkeypatch.setattr(
        "easyams.batch_tools.remove_items.Metashape",
        types.SimpleNamespace(app=fake_app),
    )
    monkeypatch.setattr(
        "easyams.batch_tools.remove_items.resolve_dialog_capabilities",
        lambda: {"Cameras": True, "Markers": True},
    )

    _get_qapp()
    dialog = BatchRemoveItemsDialog(parent=None)

    root = dialog.tree_widget.invisibleRootItem()
    chunk_item = root.child(0)
    chunk_item.setCheckState(0, Qt.CheckState.Checked)

    for index in range(dialog.item_list.count()):
        item = dialog.item_list.item(index)
        if item.text() == "Cameras":
            item.setSelected(True)

    camera_node = chunk_item.child(0)
    assert camera_node.font(0).strikeOut() is True


def test_preview_labels_follow_type_count_format():
    from easyams.batch_tools.remove_items import build_preview_for_chunk

    chunk = types.SimpleNamespace(
        cameras=[1, 2],
        markers=[1, 2, 3],
        scalebars=[],
        shapes=[],
        depth_maps=None,
        point_cloud=object(),
        model=None,
        tiled_model=None,
        elevation=None,
        orthomosaic=None,
        tie_points=object(),
    )

    preview = build_preview_for_chunk(chunk)

    assert "Cameras (2)" in preview
    assert "Markers (3)" in preview
    assert "Point Clouds (1)" in preview
    assert "Tie Points (1)" in preview
