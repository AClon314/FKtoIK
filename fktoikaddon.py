bl_info = {
    "name": "FK to IK Bone Conversion",
    "blender": (4, 2, 0),
    "category": "Animation",
    "author": "Pinpoint24, Nolca",
    "version": (1, 0, 1),
}
import os
from typing import Literal
import bpy
SELF = os.path.basename(__file__)
def Props(context: bpy.types.Context) -> 'FKtoIK_PropsGroup': return context.scene.FKtoIK_props    # type: ignore


class Logger:
    def debug(self, *args, **kwargs): print("🔍DEBUG", SELF, *args, **kwargs)
    def info(self, *args, **kwargs): print("INFO", SELF, *args, **kwargs)
    def warning(self, *args, **kwargs): print("⚠️WARN", SELF, *args, **kwargs)
    def error(self, *args, **kwargs): print("❌ERROR", SELF, *args, **kwargs)


class Progress:
    def __init__(self, *args, **kwargs): ...
    def update(self, *args, **kwargs): ...


Log = Logger()
GEN = []


def duplicate_bones(armature_name, bone_names):
    '''Duplicate specified bones in the armature'''
    bpy.ops.object.mode_set(mode='OBJECT')
    armature = bpy.data.objects.get(armature_name)
    if not armature:
        Log.error("Armature not found.")
        return

    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')

    if "IK" not in armature.data.collections:
        ik_collection = armature.data.collections.new("IK")
    else:
        ik_collection = armature.data.collections["IK"]
    dup_bone_names = []
    for bone_name in bone_names:
        if bone_name in armature.data.edit_bones:
            original_bone = armature.data.edit_bones[bone_name]
            new_bone = armature.data.edit_bones.new(original_bone.name + ".IK")
            dup_bone_names.append(new_bone.name)
            ik_collection.assign(new_bone)
            new_bone.length = original_bone.length
            new_bone.matrix = original_bone.matrix.copy()
        else:
            Log.error(f"Bone named '{bone_name}' not found.")

    bpy.ops.object.mode_set(mode='OBJECT')
    Log.debug(f"BONES DUPLICATED: '{dup_bone_names}'")
    return dup_bone_names


def add_constraints(armature_name, bone_names, target_names):
    # Add constraints to the duplicated bones
    bpy.ops.object.mode_set(mode='OBJECT')
    armature = bpy.data.objects.get(armature_name)
    if not armature:
        Log.error("Armature not found.")
        return

    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    for bone_name, target_name in zip(bone_names, target_names):
        bone = armature.pose.bones.get(bone_name)
        if bone:
            copy_loc = bone.constraints.new('COPY_LOCATION')
            copy_loc.target = armature
            copy_loc.subtarget = target_name
            copy_rot = bone.constraints.new('COPY_ROTATION')
            copy_rot.target = armature
            copy_rot.subtarget = target_name
        else:
            Log.error(f"Bone named '{bone_name}' not found in the armature.")

    bpy.ops.object.mode_set(mode='OBJECT')
    Log.debug("successfully added constraints")


def bake_animation_to_keyframes(armature_name, bone_names, frame_start, frame_end):
    # Bake animation to keyframes for the specified bones
    bpy.ops.object.mode_set(mode='OBJECT')
    armature = bpy.data.objects.get(armature_name)
    if not armature:
        Log.error("Armature not found.")
        return

    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='DESELECT')

    for bone_name in bone_names:
        bone = armature.pose.bones.get(bone_name)
        if bone:
            armature.data.bones[bone_name].select = True
        else:
            Log.error(f"Bone named '{bone_name}' not found.")

    Log.debug("start bake command")
    bpy.ops.nla.bake(frame_start=frame_start, frame_end=frame_end, only_selected=True, visual_keying=True, clear_constraints=True, clear_parents=False, use_current_action=True, bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    Log.debug("successfully bake")


def clear_bone_parents(armature_name, bone_names):
    '''Clear parents of the specified bones'''
    bpy.ops.object.mode_set(mode='OBJECT')
    armature = bpy.data.objects.get(armature_name)
    if not armature:
        Log.error("Armature not found.")
        return

    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')

    edit_bones = armature.data.edit_bones
    for bone_name in bone_names:
        bone = edit_bones.get(bone_name)
        if bone:
            bone.parent = None
            Log.debug(f"Parent cleared for bone: {bone_name}")
        else:
            Log.error(f"Bone named '{bone_name}' not found in the armature.")

    bpy.ops.object.mode_set(mode='OBJECT')
    Log.debug("successfully cleared bone parents")


def cleanup(armature_name, duplicated_bone_names):
    '''Clean up duplicated bones'''
    bpy.ops.object.mode_set(mode='OBJECT')
    armature = bpy.data.objects.get(armature_name)
    if not armature:
        Log.error("Armature not found.")
        return

    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)

    if armature.animation_data and armature.animation_data.action:
        fcurves = armature.animation_data.action.fcurves
        for fcurve in fcurves:
            for bone_name in duplicated_bone_names:
                if fcurve and fcurve.data_path.startswith("pose.bones[\"" + bone_name + "\"]"):
                    fcurves.remove(fcurve)
                    break

    bpy.ops.object.mode_set(mode='EDIT')
    for bone_name in duplicated_bone_names:
        bone = armature.data.edit_bones.get(bone_name)
        if bone:
            armature.data.edit_bones.remove(bone)
        else:
            Log.error(f"Bone named '{bone_name}' not found.")

    bpy.ops.object.mode_set(mode='OBJECT')
    Log.debug("duplicate bones cleaned up")


def get_frame_range(armature_name: str):
    '''Get the frame range of the current action of the armature'''
    armature = bpy.data.objects.get(armature_name)
    if not armature or not armature.animation_data or not armature.animation_data.action:
        raise ValueError("Armature or its action not found. Fallback to (1,1)")
    action = armature.animation_data.action
    frame_start = int(action.frame_range[0])
    frame_end = int(action.frame_range[1])
    Log.debug(f"Frame range: {frame_start} to {frame_end}")
    return frame_start, frame_end


def fk_to_ik(
    armature_name: str, bone_names: list[str],
    frame_start: int | None = None, frame_end: int | None = None,
    mode: Literal['append', 'replace'] = 'append'
):
    if frame_start is None or frame_end is None:
        start, end = get_frame_range(armature_name)
        frame_start = start if frame_start is None else frame_start
        frame_end = end if frame_end is None else frame_end
    dup_bone_names = duplicate_bones(armature_name, bone_names)
    add_constraints(armature_name, dup_bone_names, bone_names)
    bake_animation_to_keyframes(armature_name, dup_bone_names, frame_start, frame_end)
    if mode == 'append':
        clear_bone_parents(armature_name, dup_bone_names)
    elif mode == 'replace':
        clear_bone_parents(armature_name, bone_names)
        add_constraints(armature_name, bone_names, dup_bone_names)
        bake_animation_to_keyframes(armature_name, bone_names, frame_start, frame_end)
        cleanup(armature_name, dup_bone_names)


class FKtoIKOperator(bpy.types.Operator):
    bl_idname = "object.fk_to_ik"
    bl_label = "Convert"
    bl_description = "Convert selected bones from FK to IK"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = Props(context)
        return props.my_armature is not None and props.bone_list and (props.frame_start != props.frame_end)

    def execute(self, context):
        props = Props(context)
        armature_name = props.my_armature.name
        bone_names = [item.bone for item in props.bone_list]
        fk_to_ik(armature_name, bone_names, mode='replace')
        return {'FINISHED'}


class FK_append_to_IK_Operator(bpy.types.Operator):
    bl_idname = "object.fk_append_to_ik"
    bl_label = "Append"
    bl_description = "Append FK bones layer to armature, keeping the original bones"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = Props(context)
        return props.my_armature is not None and props.bone_list and (props.frame_start != props.frame_end)

    def execute(self, context):
        props = Props(context)
        armature_name = props.my_armature.name
        bone_names = [item.bone for item in props.bone_list]
        fk_to_ik(armature_name, bone_names, mode='append')
        return {'FINISHED'}


class FKtoIKPanel(bpy.types.Panel):
    # Creates a Panel in the Object properties window
    bl_label = "FK to IK"
    bl_idname = "OBJECT_PT_fk_to_ik"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Animation'

    def draw(self, context):
        layout = self.layout
        props = Props(context)

        layout.prop(props, "my_armature", text="", icon='ARMATURE_DATA')

        if props.my_armature:
            row = layout.row()
            row.template_list("BONE_UL_items", "", props, "bone_list", props, "bone_list_index", rows=2)
            col = row.column(align=True)
            col.operator("object.bone_list_get_current", icon='FILE_REFRESH', text="")
            col.operator("object.bone_list_add", icon='ADD', text="")
            col.operator("object.bone_list_remove", icon='REMOVE', text="")

        layout.operator("object.fk_to_ik", icon='CONSTRAINT_BONE')
        layout.operator("object.fk_append_to_ik", icon='GROUP_BONE')


class BoneListItem(bpy.types.PropertyGroup):
    '''Group of properties representing an item in the list'''
    bone: bpy.props.StringProperty(name="Bone")  # type: ignore


class BONE_UL_items(bpy.types.UIList):
    '''Custom UIList for displaying bones'''

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        props = Props(context)
        armature = props.my_armature

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if armature:
                layout.prop_search(item, "bone", armature.data, "bones", text="")
        elif self.layout_type in {'GRID'}:
            pass


class OBJECT_OT_BoneListGetCurrent(bpy.types.Operator):
    bl_idname = "object.bone_list_get_current"
    bl_label = "Refresh"
    bl_description = "Get current bones"

    def execute(self, context):
        props = Props(context)
        armature = props.my_armature
        if not armature:
            return {'CANCELLED'}
        props.bone_list.clear()
        for bone in armature.data.bones:
            if not any(item.bone == bone.name for item in props.bone_list):
                item = props.bone_list.add()
                item.bone = bone.name
        props.bone_list_index = 0
        return {'FINISHED'}


class OBJECT_OT_BoneListAdd(bpy.types.Operator):
    '''Add a new bone to the list'''
    bl_idname = "object.bone_list_add"
    bl_label = "Add Bone"

    def execute(self, context):
        props = Props(context)
        props.bone_list.add()
        return {'FINISHED'}


class OBJECT_OT_BoneListRemove(bpy.types.Operator):
    '''Remove the selected bone from the list'''
    bl_idname = "object.bone_list_remove"
    bl_label = "Remove Bone"

    def execute(self, context):
        props = Props(context)
        bone_list = props.bone_list
        index = props.bone_list_index
        bone_list.remove(index)
        props.bone_list_index = max(0, index - 1)
        return {'FINISHED'}


class FKtoIK_PropsGroup(bpy.types.PropertyGroup):
    my_armature: bpy.props.PointerProperty(type=bpy.types.Object, poll=lambda self, obj: obj.type == 'ARMATURE')    # type: ignore
    bone_list: bpy.props.CollectionProperty(type=BoneListItem)  # type: ignore
    bone_list_index: bpy.props.IntProperty()  # type: ignore
    frame_start: bpy.props.IntProperty(name="Frame Start", default=1)  # type: ignore
    frame_end: bpy.props.IntProperty(name="Frame End", default=250)  # type: ignore


CLASS = [
    BoneListItem,
    FKtoIK_PropsGroup,
    FKtoIKOperator,
    FK_append_to_IK_Operator,
    OBJECT_OT_BoneListGetCurrent,
    OBJECT_OT_BoneListAdd,
    OBJECT_OT_BoneListRemove,
    BONE_UL_items,
]
CLASS_UI = [
    FKtoIKPanel,
]


def register():
    [bpy.utils.register_class(cls) for cls in CLASS]
    bpy.types.Scene.FKtoIK_props = bpy.props.PointerProperty(type=FKtoIK_PropsGroup)  # type: ignore
    [bpy.utils.register_class(cls) for cls in CLASS_UI]


def unregister():
    [bpy.utils.unregister_class(cls) for cls in reversed(CLASS_UI)]
    del bpy.types.Scene.FKtoIK_props    # type: ignore
    [bpy.utils.unregister_class(cls) for cls in reversed(CLASS)]


if __name__ == "__main__":
    register()
