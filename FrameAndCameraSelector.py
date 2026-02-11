"""
FrameAndCameraSelector.py

Blender Add-on: Multi-Frame and Multi-Camera Batch Renderer

Features:
- Keep a per-scene list of camera entries (camera + frame ranges + preview toggle)
- Add/remove entries, add all cameras, enable/disable preview for all
- Fill empty frame fields using a user-provided string (supports commas and ranges)
- Batch render frames per camera using a modal operator (timer-driven)

Blender notes:
- Panel.draw must not mutate data; Operators perform mutations (this supports Undo)
- Per-scene state is stored on bpy.types.Scene properties
- Rendering is run via a modal operator to keep the UI responsive
"""

import os
import re
import bpy
from typing import List


# ---------------------------
# Data model stored in the Scene
# ---------------------------


class CameraSettings(bpy.types.PropertyGroup):
    """One entry in the batch list: camera, frame_ranges, show_preview."""

    camera: bpy.props.PointerProperty(
        name="Camera",
        type=bpy.types.Object,
        description="Camera object to use for rendering",
        poll=lambda self, obj: obj.type == "CAMERA",
    )

    frame_ranges: bpy.props.StringProperty(
        name="Frames / Ranges",
        description="Frames/ranges string, e.g. '1,5,10-20'",
        default="",
    )

    show_preview: bpy.props.BoolProperty(
        name="Show Preview",
        description="If enabled, use INVOKE render (shows render window).",
        default=True,
    )


# ---------------------------
# Helpers
# ---------------------------


def _parse_frames(frame_ranges: str) -> List[int]:
    """
    Parse a frames/ranges string into a list of integers.

    Supported syntax examples:
      '5' -> [5]
      '1,3,7' -> [1,3,7]
      '10-12' -> [10,11,12]
      '1,3-5,8' -> [1,3,4,5,8]

    Rules:
    - Tokens are comma-separated; whitespace is ignored.
    - Range tokens are 'start-end' (inclusive) and both must be integers.
    - Raises ValueError on invalid tokens or ranges.
    """
    if not frame_ranges:
        return []

    frames: List[int] = []
    tokens = [t.strip() for t in frame_ranges.split(",") if t.strip()]

    for token in tokens:
        if "-" in token:
            # Only split on the first '-' to detect malformed tokens like '1-2-3'
            parts = [p.strip() for p in token.split("-", 1)]
            if len(parts) != 2 or parts[0] == "" or parts[1] == "":
                raise ValueError(f"Invalid range token: '{token}'")

            try:
                start = int(parts[0])
                end = int(parts[1])
            except ValueError:
                raise ValueError(f"Non-integer in range: '{token}'")

            if end < start:
                raise ValueError(f"Range end < start: '{token}'")

            frames.extend(range(start, end + 1))
        else:
            try:
                frames.append(int(token))
            except ValueError:
                raise ValueError(f"Invalid frame token: '{token}'")

    return frames


def _natural_key(s: str):
    """Return a key for natural sorting: text and numeric parts.

    Produces a list of tuples where numeric parts become (0, int) and
    text parts become (1, str). This ensures stable comparisons between
    mixed tokens and sorts numbers by numeric value.
    """
    parts = re.split(r"(\d+)", (s or "").lower())
    key = []
    for p in parts:
        if p == "":
            continue
        if p.isdigit():
            key.append((0, int(p)))
        else:
            key.append((1, p))
    return key


def _file_extension_from_render(scene: bpy.types.Scene) -> str:
    """Return a typical file extension for the current image format, or ''."""
    fmt = scene.render.image_settings.file_format
    return {
        "PNG": ".png",
        "JPEG": ".jpg",
        "BMP": ".bmp",
        "TIFF": ".tiff",
        "OPEN_EXR": ".exr",
    }.get(fmt, "")


# ---------------------------
# UI Panel (Render Properties)
# ---------------------------


class CustomRenderPanel(bpy.types.Panel):
    bl_label = "Frame & Camera Selector"
    bl_idname = "RENDER_PT_custom"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        for i, cam_setting in enumerate(scene.cam_settings):
            box = layout.box()

            row = box.row()
            row.prop(cam_setting, "camera", text=f"Camera {i + 1}")
            row.operator("scene.remove_cam_setting", text="", icon="X").index = i

            box.prop(cam_setting, "frame_ranges", text="Frames / Ranges")
            box.prop(cam_setting, "show_preview", text="Show Preview")

        layout.separator()

        row = layout.row()
        row.operator("scene.add_cam_setting", text="Add Camera Setting")
        row.operator("scene.add_all_cameras", text="Add All Cameras", icon="OUTLINER_OB_CAMERA")
        row.operator("scene.delete_all_cameras", text="Delete All Cameras", icon="TRASH")

        row = layout.row(align=True)
        op = row.operator("scene.set_preview_for_all", text="Enable Preview For All", icon="HIDE_OFF")
        op.enable = True
        op = row.operator("scene.set_preview_for_all", text="Disable Preview For All", icon="HIDE_ON")
        op.enable = False

        layout.separator()

        layout.prop(scene, "mfcbr_fill_frames", text="Fill Frames / Ranges")
        layout.operator("scene.fill_empty_frame_ranges", text="Fill Empty Frame Fields", icon="KEY_HLT")

        layout.separator()
        # Highlighted render button: prefixed with a green square emoji to give a visual cue
        layout.operator("render.my_operator", text="🟩 Render Frames", icon="RENDER_STILL")


# ---------------------------
# Operators (list management)
# ---------------------------


class SCENE_OT_AddCamSetting(bpy.types.Operator):
    """Add an empty camera entry."""
    bl_idname = "scene.add_cam_setting"
    bl_label = "Add Camera Setting"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        context.scene.cam_settings.add()
        return {"FINISHED"}


class SCENE_OT_RemoveCamSetting(bpy.types.Operator):
    """Remove a camera entry by its index."""
    bl_idname = "scene.remove_cam_setting"
    bl_label = "Remove Camera Setting"
    bl_options = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty()

    def execute(self, context):
        scene = context.scene
        if 0 <= self.index < len(scene.cam_settings):
            scene.cam_settings.remove(self.index)
        return {"FINISHED"}


class SCENE_OT_AddAllCameras(bpy.types.Operator):
    """Add all cameras from the scene to the list (no duplicates)."""
    bl_idname = "scene.add_all_cameras"
    bl_label = "Add All Cameras"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        # Gather cameras not already in the list and sort them by name
        existing = {item.camera for item in scene.cam_settings if item.camera}
        added = 0

        cams = [obj for obj in scene.objects if obj.type == "CAMERA" and obj not in existing]
        cams.sort(key=lambda o: _natural_key(o.name))  # natural sort: alphabet + numeric magnitude

        for obj in cams:
            item = scene.cam_settings.add()
            item.camera = obj
            item.frame_ranges = ""
            item.show_preview = True
            added += 1

        self.report({"INFO"}, f"Added {added} camera(s) (sorted by name).")
        return {"FINISHED"}


class SCENE_OT_SetPreviewForAll(bpy.types.Operator):
    """Enable/disable render preview for all camera entries."""
    bl_idname = "scene.set_preview_for_all"
    bl_label = "Set Preview For All"
    bl_options = {"REGISTER", "UNDO"}

    enable: bpy.props.BoolProperty(default=True)

    def execute(self, context):
        scene = context.scene
        changed = 0

        for item in scene.cam_settings:
            if item.camera is None:
                continue
            if item.show_preview != self.enable:
                item.show_preview = self.enable
                changed += 1

        self.report({"INFO"}, f"Updated preview on {changed} entry(s).")
        return {"FINISHED"}


class SCENE_OT_FillEmptyFrameRanges(bpy.types.Operator):
    """Fill EMPTY 'Frames / Ranges' fields with Scene.mfcbr_fill_frames."""
    bl_idname = "scene.fill_empty_frame_ranges"
    bl_label = "Fill Empty Frame Fields"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        fill_text = (getattr(scene, "mfcbr_fill_frames", "") or "").strip()

        if not fill_text:
            self.report({"ERROR"}, "Fill Frames / Ranges is empty.")
            return {"CANCELLED"}

        try:
            frames = _parse_frames(fill_text)
        except Exception as e:
            self.report({"ERROR"}, f"Invalid frames/ranges: {e}")
            return {"CANCELLED"}

        if not frames:
            self.report({"ERROR"}, "No valid frames parsed from Fill Frames / Ranges.")
            return {"CANCELLED"}

        filled = 0
        for item in scene.cam_settings:
            if (item.frame_ranges or "").strip() == "":
                item.frame_ranges = fill_text
                filled += 1

        self.report({"INFO"}, f"Filled {filled} empty field(s).")
        return {"FINISHED"}


class SCENE_OT_DeleteAllCameras(bpy.types.Operator):
    """Remove all camera entries from the batch list (does not delete camera objects)."""
    bl_idname = "scene.delete_all_cameras"
    bl_label = "Delete All Cameras"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        count = len(scene.cam_settings)
        # Remove all items from the collection
        for i in range(count - 1, -1, -1):
            scene.cam_settings.remove(i)

        self.report({"INFO"}, f"Removed {count} camera entry(ies).")
        return {"FINISHED"}


# ---------------------------
# Render logic (jobs + modal)
# ---------------------------


class RenderJob:
    """Render task for one camera entry; renders its frame list sequentially."""

    def __init__(self, index: int, cam_setting: CameraSettings):
        self.index = index
        self.cam_setting = cam_setting
        self.frames: List[int] = []
        self.is_running = False
        self.is_cancelled = False
        self.original_filepath = ""

    def start(self, context):
        scene = context.scene

        if not self.cam_setting.camera or self.cam_setting.camera.type != "CAMERA":
            print("MFCBR --- Skipping job: camera not set/invalid")
            self.finish()
            return

        try:
            self.frames = _parse_frames(self.cam_setting.frame_ranges)
        except Exception as e:
            print(f"MFCBR --- Invalid frame ranges for {self.cam_setting.camera.name}: {e}")
            self.finish()
            return

        if not self.frames:
            print(f"MFCBR --- Skipping job: no frames for {self.cam_setting.camera.name}")
            self.finish()
            return

        self.original_filepath = scene.render.filepath
        out_dir = bpy.path.abspath(self.original_filepath)
        if not os.path.isdir(out_dir):
            print("MFCBR --- Output path is not a directory. Set Render Output to a folder.")
            self.finish()
            return

        # Set the active camera for this job
        scene.camera = self.cam_setting.camera

        # Start rendering frames for this job
        self.render_next_frame(context)
        bpy.app.handlers.render_cancel.append(self.render_cancel_handler)

    def render_next_frame(self, context):
        if self.frames and not self.is_cancelled:
            frame = self.frames.pop(0)
            scene = context.scene
            scene.frame_set(frame)

            ext = _file_extension_from_render(scene)
            check_filepath = os.path.join(
                self.original_filepath,
                f"{self.cam_setting.camera.name}_frame{frame}{ext}",
            )

            filepath = os.path.join(self.original_filepath, f"{self.cam_setting.camera.name}_frame{frame}")
            scene.render.filepath = filepath

            # If overwrite disabled and file exists, skip
            if (not scene.render.use_overwrite) and ext and os.path.isfile(bpy.path.abspath(check_filepath)):
                print(f"MFCBR --- Skipping existing: {check_filepath}")
                def _mark_running():
                    self.is_running = True
                bpy.app.timers.register(_mark_running)
                bpy.app.timers.register(lambda: self.render_next_frame(bpy.context), first_interval=0.1)
                return

            # Continue after each frame using render_post handler
            bpy.app.handlers.render_post.append(self.render_post_handler)

            print(f"MFCBR --- Rendering frame {frame} with {self.cam_setting.camera.name}")

            def _mark_running():
                self.is_running = True
            bpy.app.timers.register(_mark_running)

            bpy.ops.render.render(
                "INVOKE_DEFAULT" if self.cam_setting.show_preview else "EXEC_DEFAULT",
                write_still=True,
            )
        else:
            self.finish()

    def render_cancel_handler(self, scene, dummy):
        try:
            bpy.app.handlers.render_cancel.remove(self.render_cancel_handler)
        except ValueError:
            pass

        print("MFCBR --- Render cancelled")

        def _mark_cancelled():
            self.is_cancelled = True
        bpy.app.timers.register(_mark_cancelled)

    def render_post_handler(self, scene, dummy):
        try:
            bpy.app.handlers.render_post.remove(self.render_post_handler)
        except ValueError:
            pass

        if not self.is_cancelled:
            bpy.app.timers.register(lambda: self.render_next_frame(bpy.context), first_interval=0.1)

    def finish(self):
        def _finish():
            self.is_running = False
            if self.original_filepath:
                bpy.context.scene.render.filepath = self.original_filepath
            if self.cam_setting.camera:
                print(f"MFCBR --- Finished job for {self.cam_setting.camera.name}")
        bpy.app.timers.register(_finish)


class RenderOperator(bpy.types.Operator):
    """Modal operator that iterates through RenderJobs."""
    bl_idname = "render.my_operator"
    bl_label = "Render Frames"
    bl_options = {"REGISTER"}

    _timer = None
    _jobs: List[RenderJob] = []
    _current_job = None

    def execute(self, context):
        # Build a job queue from current scene.cam_settings
        self._jobs = [RenderJob(i, cs) for i, cs in enumerate(context.scene.cam_settings)]
        self._current_job = None

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.25, window=context.window)
        wm.modal_handler_add(self)

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type == "TIMER":
            if self._current_job is not None and self._current_job.is_cancelled:
                return self.cancel(context)

            if self._current_job is None or not self._current_job.is_running:
                if self._jobs:
                    self._current_job = self._jobs.pop(0)
                    self._current_job.start(context)
                else:
                    return self.cancel(context)

        return {"PASS_THROUGH"}

    def cancel(self, context):
        wm = context.window_manager
        if self._timer is not None:
            wm.event_timer_remove(self._timer)
            self._timer = None

        if self._current_job:
            self._current_job.finish()

        print("MFCBR --- All camera jobs completed.")
        return {"CANCELLED"}


# ---------------------------
# Registration
# ---------------------------


_CLASSES = (
    CameraSettings,
    CustomRenderPanel,
    SCENE_OT_AddCamSetting,
    SCENE_OT_AddAllCameras,
    SCENE_OT_DeleteAllCameras,
    SCENE_OT_SetPreviewForAll,
    SCENE_OT_FillEmptyFrameRanges,
    SCENE_OT_RemoveCamSetting,
    RenderOperator,
)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)

    bpy.types.Scene.cam_settings = bpy.props.CollectionProperty(type=CameraSettings)

    bpy.types.Scene.mfcbr_fill_frames = bpy.props.StringProperty(
        name="Fill Frames / Ranges",
        description="Frames/ranges to insert into empty frame fields (e.g. 1,5,10-20)",
        default="1",
    )


def unregister():
    if hasattr(bpy.types.Scene, "cam_settings"):
        del bpy.types.Scene.cam_settings
    if hasattr(bpy.types.Scene, "mfcbr_fill_frames"):
        del bpy.types.Scene.mfcbr_fill_frames

    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
