bl_info = {
    "name": "CheeseOFcheese - Multiple Frame and Camera Batch Render",
    "author": "Victor Do, CheeseOFcheese",
    "version": (2, 3),
    "blender": (2, 80, 0),
    "location": "Render Properties > Custom Render Panel",
    "description": "Allows specifying custom frames or frame ranges and multiple cameras for rendering in batches",
    "category": "Render",
}

import bpy
import os

class CameraSettings(bpy.types.PropertyGroup):
    camera: bpy.props.PointerProperty(
        name="Camera",
        type=bpy.types.Object,
        description="Camera to use for rendering",
        poll=lambda self, obj: obj.type == 'CAMERA',
    )
    frame_ranges: bpy.props.StringProperty(
        name="Frame Ranges",
        description="Specify frames or frame ranges separated by commas. For example: 11,25,250 or 25-40",
        default="",
    )
    show_preview: bpy.props.BoolProperty(
        name="Show Preview",
        description="If checked, the render will show a preview (uses more RAM)",
        default=True,
    )

class CustomRenderPanel(bpy.types.Panel):
    bl_label = "Frame & Camera Selector - Render Panel"
    bl_idname = "RENDER_PT_custom"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        for i, cam_setting in enumerate(scene.cam_settings):
            box = layout.box()
            row = box.row()
            row.prop(cam_setting, "camera", text=f"Camera {i+1}")
            row.operator("scene.remove_cam_setting", text="", icon='X').index = i
            box.prop(cam_setting, "frame_ranges", text="Frames or Frame Ranges")
            box.prop(cam_setting, "show_preview", text="Show Preview")

        layout.operator("scene.add_cam_setting", text="Add Camera Setting")
        layout.operator("render.cheese_batch_render", text="Render Frames")

class SCENE_OT_AddCamSetting(bpy.types.Operator):
    bl_idname = "scene.add_cam_setting"
    bl_label = "Add Camera Setting"

    def execute(self, context):
        context.scene.cam_settings.add()
        return {'FINISHED'}

class SCENE_OT_RemoveCamSetting(bpy.types.Operator):
    bl_idname = "scene.remove_cam_setting"
    bl_label = "Remove Camera Setting"
    index: bpy.props.IntProperty()

    def execute(self, context):
        context.scene.cam_settings.remove(self.index)
        return {'FINISHED'}

class RenderJob:
    def __init__(self, cam_setting):
        self.cam_setting = cam_setting
        self.frames = self._parse_frame_ranges(cam_setting.frame_ranges)
        self.is_running = False
        self.is_cancelled = False
        self.original_filepath = bpy.context.scene.render.filepath

    def _parse_frame_ranges(self, frame_ranges):
        frames = []
        for frame_range in frame_ranges.split(','):
            if '-' in frame_range:
                start_frame, end_frame = map(int, frame_range.split('-'))
                frames.extend(range(start_frame, end_frame + 1))
            else:
                try:
                    frames.append(int(frame_range))
                except ValueError:
                    print(f"CheeseOFcheese --- Invalid frame range: {frame_range}")
        return frames

    def start(self):
        if not self.cam_setting.camera:
            print("CheeseOFcheese --- No camera assigned to the setting. Skipping...")
            self.finish()
            return

        bpy.context.scene.camera = self.cam_setting.camera
        print(f"CheeseOFcheese --- Starting render for camera: {self.cam_setting.camera.name}")
        self.render_next_frame()

    def render_next_frame(self):
        if self.frames and not self.is_cancelled:
            frame = self.frames.pop(0)
            scene = bpy.context.scene
            scene.frame_set(frame)

            file_format = scene.render.image_settings.file_format.lower()
            file_extension = f".{file_format}"
            filepath = os.path.join(self.original_filepath, f"{self.cam_setting.camera.name}_frame{frame}{file_extension}")
            scene.render.filepath = filepath

            if not scene.render.use_overwrite and os.path.isfile(bpy.path.abspath(filepath)):
                print(f"CheeseOFcheese --- Skipping frame {frame} with {self.cam_setting.camera.name} because it has already been rendered")
                self.render_next_frame()
            else:
                self.is_running = True
                bpy.app.handlers.render_post.append(self.render_post_handler)
                bpy.ops.render.render('INVOKE_DEFAULT' if self.cam_setting.show_preview else 'EXEC_DEFAULT', write_still=True)
        else:
            self.finish()

    def render_post_handler(self, scene):
        bpy.app.handlers.render_post.remove(self.render_post_handler)
        print(f"CheeseOFcheese --- Finished rendering frame {scene.frame_current} with {self.cam_setting.camera.name}")
        self.is_running = False

        if not self.is_cancelled:
            self.render_next_frame()

    def finish(self):
        self.is_running = False
        bpy.context.scene.render.filepath = self.original_filepath
        print(f"CheeseOFcheese --- Finished rendering all frames with {self.cam_setting.camera.name}")

class RenderOperator(bpy.types.Operator):
    bl_idname = "render.cheese_batch_render"
    bl_label = "Cheese Batch Render Operator"

    _jobs = []
    _current_job = None

    def execute(self, context):
        self._jobs = [RenderJob(cam_setting) for cam_setting in context.scene.cam_settings if cam_setting.camera]
        print("CheeseOFcheese --- Render jobs initialized:", self._jobs)

        if not self._jobs:
            self.report({'WARNING'}, "No valid render jobs found. Please add camera settings.")
            return {'CANCELLED'}

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            if self._current_job is None or not self._current_job.is_running:
                if self._jobs:
                    self._current_job = self._jobs.pop(0)
                    self._current_job.start()
                else:
                    return self.cancel(context)

        return {'PASS_THROUGH'}

    def cancel(self, context):
        if self._current_job:
            self._current_job.finish()
        print("CheeseOFcheese --- All camera jobs completed.")
        return {'CANCELLED'}

def register():
    bpy.utils.register_class(CameraSettings)
    bpy.types.Scene.cam_settings = bpy.props.CollectionProperty(type=CameraSettings)
    bpy.utils.register_class(CustomRenderPanel)
    bpy.utils.register_class(SCENE_OT_AddCamSetting)
    bpy.utils.register_class(SCENE_OT_RemoveCamSetting)
    bpy.utils.register_class(RenderOperator)

def unregister():
    del bpy.types.Scene.cam_settings
    bpy.utils.unregister_class(CameraSettings)
    bpy.utils.unregister_class(CustomRenderPanel)
    bpy.utils.unregister_class(SCENE_OT_AddCamSetting)
    bpy.utils.unregister_class(SCENE_OT_RemoveCamSetting)
    bpy.utils.unregister_class(RenderOperator)

if __name__ == "__main__":
    register()
