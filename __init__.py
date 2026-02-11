bl_info = {
    "name": "Multiple Frame and Camera Batch Render",
    "author": "Victor Do, cheeseOFcheese",
    "version": (2, 2),
    "blender": (2, 80, 0),
    "location": "Render Properties > Custom Render Panel",
    "description": "Allows specifying custom frames or frame ranges and multiple cameras for rendering in batches",
    "category": "Render",
}

# Package entry point:
# - keep __init__.py lightweight
# - delegate registration to the implementation module

import importlib

from . import FrameAndCameraSelector as _core


def register():
    # Useful for dev workflows (Reload Scripts / live editing)
    importlib.reload(_core)
    _core.register()


def unregister():
    _core.unregister()
