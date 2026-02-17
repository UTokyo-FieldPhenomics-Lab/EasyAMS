import os
import sys
import types


def _install_metashape_stub() -> None:
    """Install a lightweight Metashape stub for local pytest runs."""
    if "Metashape" in sys.modules:
        return

    app_stub = types.SimpleNamespace(
        document=types.SimpleNamespace(chunks=[]),
        addMenuItem=lambda *_args, **_kwargs: None,
        addMenuSeparator=lambda *_args, **_kwargs: None,
    )
    module_stub = types.ModuleType("Metashape")
    setattr(module_stub, "app", app_stub)
    sys.modules["Metashape"] = module_stub


_install_metashape_stub()

import easyams as ams

if not os.path.exists("tests/outputs"):
    os.makedirs("tests/outputs", exist_ok=True)
