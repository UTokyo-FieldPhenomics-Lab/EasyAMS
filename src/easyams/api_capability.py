"""Runtime API capability resolver for remove-items support."""

import copy
import json
from typing import Dict, List, Tuple

import Metashape


SCHEMA_VERSION = "2026.02.17"
GENERATED_FROM = "tests/pdfs/metashape_python_api_1_5_0..2_2_1.pdf"

REMOVE_ITEMS_CAPABILITY_BY_VERSION = {
    "1.5.0": {
        "supports": {
            "Cameras": True,
            "Masks": False,
            "Markers": True,
            "Thumbnails": False,
            "Scale Bars": True,
            "Shapes": True,
            "Depth Maps": False,
            "Point Clouds": False,
            "Laser Scans": False,
            "Models": False,
            "Textures": False,
            "Tiled Models": False,
            "Elevation Models": False,
            "Orthomosaics": False,
            "Tie Points": False,
        }
    },
    "2.1.3": {
        "supports": {
            "Cameras": True,
            "Masks": False,
            "Markers": True,
            "Thumbnails": False,
            "Scale Bars": True,
            "Shapes": True,
            "Depth Maps": True,
            "Point Clouds": True,
            "Laser Scans": False,
            "Models": True,
            "Textures": False,
            "Tiled Models": True,
            "Elevation Models": True,
            "Orthomosaics": True,
            "Tie Points": False,
        }
    },
    "2.2.1": {
        "supports": {
            "Cameras": True,
            "Masks": False,
            "Markers": True,
            "Thumbnails": False,
            "Scale Bars": True,
            "Shapes": True,
            "Depth Maps": True,
            "Point Clouds": True,
            "Laser Scans": False,
            "Models": True,
            "Textures": False,
            "Tiled Models": True,
            "Elevation Models": True,
            "Orthomosaics": True,
            "Tie Points": False,
        }
    },
}


def get_metashape_version() -> str:
    """Get the current Metashape semantic version.

    Returns
    -------
    str
        Version string from ``Metashape.app.version``.

    Examples
    --------
    >>> isinstance(get_metashape_version(), str)
    True
    """
    return getattr(Metashape.app, "version", "0.0.0")


def load_api_capability() -> Dict[str, Dict]:
    """Load built-in remove-items capability matrix.

    Returns
    -------
    Dict[str, Dict]
        Matrix metadata and per-version capability entries.

    Examples
    --------
    >>> "versions" in load_api_capability()
    True
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_from": GENERATED_FROM,
        "versions": copy.deepcopy(REMOVE_ITEMS_CAPABILITY_BY_VERSION),
    }


def _version_key(version: str) -> Tuple[int, int, int]:
    """Build sortable semantic-version tuple from string."""
    parts: List[str] = version.split(".")
    numbers = [int(part) for part in parts[:3] if part.isdigit()]
    while len(numbers) < 3:
        numbers.append(0)
    return numbers[0], numbers[1], numbers[2]


def _get_config_manager():
    """Fetch EasyAMS runtime config manager lazily."""
    from . import system_info

    return system_info.config_manager


def read_runtime_sync_state() -> Dict[str, Dict]:
    """Read runtime capability sync state from config storage.

    Returns
    -------
    Dict[str, Dict]
        Runtime map keyed by Metashape version.
    """
    manager = _get_config_manager()
    value = manager.load("api_capability_sync_state")
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}


def write_runtime_sync_state(state: Dict[str, Dict]) -> None:
    """Persist runtime capability sync state to config storage.

    Parameters
    ----------
    state : Dict[str, Dict]
        Runtime capability map keyed by version.
    """
    manager = _get_config_manager()
    manager.save("api_capability_sync_state", state)


def _nearest_known_lower(target_version: str, versions: Dict[str, Dict]) -> str:
    """Pick nearest lower known version or fallback to latest known."""
    sorted_versions = sorted(versions.keys(), key=_version_key)
    target_key = _version_key(target_version)
    lower_or_equal = [
        version for version in sorted_versions if _version_key(version) <= target_key
    ]
    if lower_or_equal:
        return lower_or_equal[-1]
    return sorted_versions[-1]


def probe_api_capabilities(version: str, base_caps: Dict[str, Dict]) -> Dict[str, Dict]:
    """Probe runtime API capability and update baseline map.

    Notes
    -----
    Current implementation keeps baseline values and stamps probe metadata.

    Parameters
    ----------
    version : str
        Current Metashape version string.
    base_caps : Dict[str, Dict]
        Baseline capability entry for this version.

    Returns
    -------
    Dict[str, Dict]
        Probed capability entry.
    """
    probed = copy.deepcopy(base_caps)
    probed["_probed"] = True
    probed["_probe_version"] = version
    return probed


def resolve_capabilities_for_current_version() -> Dict[str, Dict]:
    """Resolve runtime capability entry for current Metashape version.

    Returns
    -------
    Dict[str, Dict]
        Capability entry for current version with sync metadata.
    """
    matrix = load_api_capability()["versions"]
    runtime = read_runtime_sync_state()
    current_version = get_metashape_version()

    existing = runtime.get(current_version, {})
    if existing.get("synced") is True:
        return existing

    source_version = current_version
    if current_version in matrix:
        base_caps = copy.deepcopy(existing or matrix[current_version])
    else:
        source_version = _nearest_known_lower(current_version, matrix)
        base_caps = copy.deepcopy(matrix[source_version])

    resolved = probe_api_capabilities(current_version, base_caps)
    resolved["_source_version"] = source_version
    resolved["_probed"] = True
    resolved["synced"] = True
    runtime[current_version] = resolved
    write_runtime_sync_state(runtime)
    return resolved
