bl_info = {
    "name": "FK to IK Bone Conversion",
    "blender": (4, 2, 0),
    "category": "Animation",
    "author": "Pinpoint24, Nolca",
    "version": (1, 1, 0),
}
import os
import bpy
from typing import Callable, Literal, ParamSpec, TypeVar, cast

_PS = ParamSpec("_PS")
_TV = TypeVar("_TV")
SELF = os.path.basename(__file__)
OWNER = object()


def Props(context: bpy.types.Context) -> "FKtoIK_PropsGroup":
    return context.scene.FKtoIK_props  # type: ignore


def copy_args(func: Callable[_PS, _TV]):
    def return_func(func: Callable[..., _TV]) -> Callable[_PS, _TV]:
        return cast(Callable[_PS, _TV], func)

    return return_func


class Logger:
    def debug(self, *args, **kwargs):
        print("🔍DEBUG", SELF, *args, **kwargs)

    def info(self, *args, **kwargs):
        print("INFO", SELF, *args, **kwargs)

    def warning(self, *args, **kwargs):
        print("⚠️WARN", SELF, *args, **kwargs)

    def error(self, *args, **kwargs):
        print("❌ERROR", SELF, *args, **kwargs)


class Progress:
    def __init__(self, *args, **kwargs): ...
    def update(self, *args, **kwargs): ...


Log = Logger()
GEN = []


def duplicate_bones(armature_name, bone_names):
    """Duplicate specified bones in the armature"""
    bpy.ops.object.mode_set(mode="OBJECT")
    armature = bpy.data.objects.get(armature_name)
    if not (armature and isinstance(armature.data, bpy.types.Armature)):
        Log.error("Armature not found.")
        return

    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

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

    bpy.ops.object.mode_set(mode="OBJECT")
    Log.debug(f"BONES DUPLICATED: '{dup_bone_names}'")
    return dup_bone_names


def add_constraints(armature_name, bone_names, target_names, no_scale=False):
    """Add constraints to the duplicated bones"""
    bpy.ops.object.mode_set(mode="OBJECT")
    armature = bpy.data.objects.get(armature_name)
    if not armature:
        Log.error("Armature not found.")
        return

    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="POSE")

    for bone_name, target_name in zip(bone_names, target_names):
        bone = armature.pose.bones.get(bone_name)
        if bone:
            for t in (
                ["COPY_LOCATION", "COPY_ROTATION"] if no_scale else ["COPY_TRANSFORMS"]
            ):
                add_constraint(bone, t, armature, target_name)
        else:
            Log.error(f"Bone named '{bone_name}' not found in the armature.")

    bpy.ops.object.mode_set(mode="OBJECT")
    Log.debug("successfully added constraints")


def add_constraint(bone: bpy.types.PoseBone, type: str, armature, bone_name):
    con = bone.constraints.new(type)
    con.target = armature
    con.subtarget = bone_name
    return con


def bake_animation_to_keyframes(
    armature_name, bone_names, frame_start, frame_end, clear_parents=True
):
    # Bake animation to keyframes for the specified bones
    bpy.ops.object.mode_set(mode="OBJECT")
    armature = bpy.data.objects.get(armature_name)
    if not armature:
        Log.error("Armature not found.")
        return

    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="DESELECT")

    for bone_name in bone_names:
        bone = armature.pose.bones.get(bone_name)
        if bone:
            armature.data.bones[bone_name].select = True
        else:
            Log.error(f"Bone named '{bone_name}' not found.")

    Log.debug("start bake command")
    # TODO: if dup_bone_names is already dup, don't use current action by default
    pg = Progress(frame_start, frame_end)
    for i in range(frame_start, frame_end + 1):
        bpy.ops.nla.bake(
            frame_start=i,
            frame_end=i,
            only_selected=True,
            visual_keying=True,
            clear_constraints=False,
            clear_parents=False,
            use_current_action=True,
            bake_types={"POSE"},
        )
        pg.update()
        yield
    bpy.ops.nla.bake(
        frame_start=0,
        frame_end=0,
        only_selected=True,
        clear_constraints=True,
        use_current_action=True,
        bake_types={"POSE"},
        clear_parents=clear_parents,
    )
    bpy.ops.object.mode_set(mode="OBJECT")
    Log.debug("successfully bake")


def clear_bone_parents(armature_name, bone_names):
    """Clear parents of the specified bones"""
    bpy.ops.object.mode_set(mode="OBJECT")
    armature = bpy.data.objects.get(armature_name)
    if not armature:
        Log.error("Armature not found.")
        return

    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    edit_bones = armature.data.edit_bones
    for bone_name in bone_names:
        bone = edit_bones.get(bone_name)
        if bone:
            bone.parent = None
            Log.debug(f"Parent cleared for bone: {bone_name}")
        else:
            Log.error(f"Bone named '{bone_name}' not found in the armature.")

    bpy.ops.object.mode_set(mode="OBJECT")
    Log.debug("successfully cleared bone parents")


def cleanup(armature_name, duplicated_bone_names):
    """Clean up duplicated bones"""
    bpy.ops.object.mode_set(mode="OBJECT")
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
                if fcurve and fcurve.data_path.startswith(
                    'pose.bones["' + bone_name + '"]'
                ):
                    fcurves.remove(fcurve)
                    break

    bpy.ops.object.mode_set(mode="EDIT")
    for bone_name in duplicated_bone_names:
        bone = armature.data.edit_bones.get(bone_name)
        if bone:
            armature.data.edit_bones.remove(bone)
        else:
            Log.error(f"Bone named '{bone_name}' not found.")

    bpy.ops.object.mode_set(mode="OBJECT")
    Log.debug("duplicate bones cleaned up")


def get_frame_range(armature_name: str):
    """Get the frame range of the current action of the armature"""
    armature = bpy.data.objects.get(armature_name)
    if (
        not armature
        or not armature.animation_data
        or not armature.animation_data.action
    ):
        raise ValueError("Armature or its action not found. Fallback to (1,1)")
    action = armature.animation_data.action
    frame_start = int(action.frame_range[0])
    frame_end = int(action.frame_range[1])
    Log.debug(f"Frame range: {frame_start} to {frame_end}")
    return frame_start, frame_end


def gen_fk_to_ik(
    armature_name: str,
    bone_names: list[str],
    frame_start: int | None = None,
    frame_end: int | None = None,
    mode: Literal["append", "replace"] = "append",
    no_scale=False,
):
    if frame_start is None or frame_end is None:
        start, end = get_frame_range(armature_name)
        frame_start = start if frame_start is None else frame_start
        frame_end = end if frame_end is None else frame_end
    dup_bone_names = duplicate_bones(armature_name, bone_names)
    add_constraints(armature_name, dup_bone_names, bone_names, no_scale=no_scale)
    yield from bake_animation_to_keyframes(
        armature_name,
        dup_bone_names,
        frame_start,
        frame_end,
        clear_parents=(mode == "append"),
    )
    if mode == "replace":
        clear_bone_parents(armature_name, bone_names)
        add_constraints(armature_name, bone_names, dup_bone_names, no_scale=no_scale)
        yield from bake_animation_to_keyframes(
            armature_name, bone_names, frame_start, frame_end
        )
        cleanup(armature_name, dup_bone_names)


@copy_args(gen_fk_to_ik)  # type: ignore
def fk_to_ik(*args, **kwargs):
    gen = gen_fk_to_ik(*args, **kwargs)
    while True:
        try:
            next(gen)
        except StopIteration:
            break


class FKtoIKOperator(bpy.types.Operator):
    bl_idname = "object.fk_to_ik"
    bl_label = "Convert"
    bl_description = "Convert bones from FK to IK"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        props = Props(context)
        return (
            props.src_armature is not None
            and props.bone_list
            and (props.frame_start != props.frame_end)
        )

    def execute(self, context):
        props = Props(context)
        armature_name = props.src_armature.name
        bone_names = [item.bone for item in props.bone_list]
        fk_to_ik(armature_name, bone_names, mode="replace")
        return {"FINISHED"}


class FK_append_to_IK_Operator(bpy.types.Operator):
    bl_idname = "object.fk_append_to_ik"
    bl_label = "Append"
    bl_description = "Convert FK then append the IK bones layer to armature, keeping the original bones"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        props = Props(context)
        return (
            props.src_armature is not None
            and props.bone_list
            and (props.frame_start != props.frame_end)
        )

    def execute(self, context):
        props = Props(context)
        armature_name = props.src_armature.name
        bone_names = [item.bone for item in props.bone_list]
        fk_to_ik(
            armature_name, bone_names, mode="append", no_scale=not props.is_copy_scale
        )
        return {"FINISHED"}


class FKtoIKPanel(bpy.types.Panel):
    # Creates a Panel in the Object properties window
    bl_label = "FK to IK"
    bl_idname = "OBJECT_PT_fk_to_ik"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Animation"

    def draw(self, context):
        layout = self.layout
        assert layout
        props = Props(context)

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(props, "mapping_preset", icon="GROUP_BONE", text="")
        row.operator("wm.open_dir_mapping", icon="FILE_FOLDER", text="")

        if props.mapping_preset != "new":
            return
        row = col.row(align=True)
        _row = row.row(align=True)
        _row.prop(
            props,
            "src_armature",
            text="",
            placeholder="Source",
            icon="ARMATURE_DATA",
        )
        _row.enabled = not props.is_current_selected
        row.prop(
            props,
            "is_current_selected",
            text="",
            icon=(
                "RESTRICT_SELECT_OFF"
                if props.is_current_selected
                else "RESTRICT_SELECT_ON"
            ),
        )
        row = col.column(align=True)
        if not props.src_armature:
            return
        # row.prop(
        #     props,
        #     "dst_armature",
        #     text="",
        #     placeholder="Target",
        #     icon="ARMATURE_DATA",
        # )

        row = layout.row()
        row.template_list(
            "BONE_UL_items", "", props, "bone_list", props, "bone_list_index", rows=1
        )
        col = row.column(align=True)
        col.operator("object.bone_list_get_current", icon="FILE_REFRESH", text="")
        col.operator("object.bone_list_add", icon="ADD", text="")
        col.operator("object.bone_list_remove", icon="REMOVE", text="")
        col.operator("object.bone_list_export", icon="EXPORT", text="")

        layout.prop(props, "is_copy_scale", text="Copy Scale")
        col = layout.column(align=True)
        col.operator("object.fk_to_ik", icon="BONE_DATA")
        row = col.row(align=True)
        row.operator("object.fk_append_to_ik", icon="GROUP_BONE")
        row.prop(props, "bone_layer_fallback", icon="ADD", text="")

        row = layout.row(align=True)
        sx, sy = get_scale()
        row.label(
            text=f"region{bpy.context.region.width} area{bpy.context.area.width} scale{sx:.2f},{sy:.2f} base{bpy.context.preferences.system.ui_scale}"  # type: ignore
        )


class BoneListItem(bpy.types.PropertyGroup):
    """Group of properties representing an item in the list"""

    src_bone: bpy.props.StringProperty(name="Source FK Bone")  # type: ignore
    dst_bone: bpy.props.StringProperty(name="Destination IK Bone")  # type: ignore

    @staticmethod
    def remove_empty(props):
        """移除src_bone和dst_bone都为空的项"""
        items_to_remove = []
        for i, item in enumerate(props.bone_list):
            if not item.src_bone and not item.dst_bone:
                items_to_remove.append(i)

        # 从后往前删除，避免索引变化影响删除操作
        for i in reversed(items_to_remove):
            if i < len(props.bone_list):
                props.bone_list.remove(i)


class BONE_UL_items(bpy.types.UIList):
    """Custom UIList for displaying bones"""

    def draw_item(
        self,
        context,
        layout: bpy.types.UILayout,
        data,
        item,
        icon,
        active_data,
        active_propname,
        index,
    ):
        props = Props(context)
        if not props.src_armature or not isinstance(
            props.src_armature.data, bpy.types.Armature
        ):
            return
        src = props.src_armature
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            is_dstBone_in_srcArmature = item.dst_bone in src.data.bones
            split = layout.split(
                factor=(
                    0.5
                    if is_dstBone_in_srcArmature
                    else min(
                        0.95, max(0.05, 1 - ((bpy.context.region.width - 85) / 1700))
                    )
                ),
                align=True,
            )
            split.prop_search(item, "src_bone", src.data, "bones", text="")
            split.prop_search(
                item,
                "dst_bone",
                src.data,
                "bones",
                text="",
                icon="RIGHTARROW" if is_dstBone_in_srcArmature else "ADD",
                results_are_suggestions=True,
            )
            # TODO: use dst.data when NOT dst_armature == src_armature
        elif self.layout_type in {"GRID"}:
            ...

    def filter_items(self, context, data, propname):
        bone_list = getattr(data, propname, [])
        flt_flags = []
        flt_neworder = []

        # 如果有文本过滤器，则应用过滤
        if self.filter_name:
            flt_flags = bpy.types.UI_UL_list.filter_items_by_name(
                self.filter_name,
                self.bitflag_filter_item,
                bone_list,
                "src_bone",
                reverse=False,
            )

        # 如果没有过滤器标志，则初始化为所有项都可见
        if not flt_flags:
            flt_flags = [self.bitflag_filter_item] * len(bone_list)

        return flt_flags, flt_neworder


class OBJECT_OT_BoneListGetCurrent(bpy.types.Operator):
    "Get current selected bones, need to be in Edit or Pose mode ⚠️"

    bl_idname = "object.bone_list_get_current"
    bl_label = "Refresh"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = Props(context)
        armature: bpy.types.Object = props.src_armature
        if not (armature and isinstance(armature.data, bpy.types.Armature)):
            return {"CANCELLED"}
        props.bone_list.clear()

        bones = []
        if context.mode == "EDIT_ARMATURE":
            bones = [b for b in armature.data.edit_bones if b.select]
        elif context.mode == "POSE":
            bones = [b for b in armature.pose.bones if b.bone.select]
        if not bones:
            bones = armature.data.bones

        for bone in bones:
            item = props.bone_list.add()
            item.src_bone = bone.name
        props.bone_list_index = 0
        return {"FINISHED"}


class OBJECT_OT_BoneListAdd(bpy.types.Operator):
    """Add a new bone to the list"""

    bl_idname = "object.bone_list_add"
    bl_label = "Add Bone"

    def execute(self, context):
        props = Props(context)
        props.bone_list.add()
        return {"FINISHED"}


class OBJECT_OT_BoneListRemove(bpy.types.Operator):
    """Remove the selected bone from the list"""

    bl_idname = "object.bone_list_remove"
    bl_label = "Remove"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = Props(context)
        bone_list = props.bone_list
        index = props.bone_list_index
        bone_list.remove(index)
        props.bone_list_index = max(0, index - 1)
        return {"FINISHED"}


class OBJECT_OT_BoneListExport(bpy.types.Operator):
    """Export the selected bones to a preset"""

    bl_idname = "object.bone_list_export"
    bl_label = "Export"

    def execute(self, context):
        props = Props(context)
        armature = props.src_armature
        if not (armature and isinstance(armature.data, bpy.types.Armature)):
            return {"CANCELLED"}

        # Get the selected bones
        selected_bones = [b for b in armature.data.bones if b.select]
        if not selected_bones:
            self.report({"WARNING"}, "No bones selected")
            return {"CANCELLED"}

        # Export the bone list to a file
        file_path = bpy.path.abspath("//bone_list.txt")
        with open(file_path, "w") as f:
            for bone in selected_bones:
                f.write(f"{bone.name}\n")

        self.report({"INFO"}, f"Bone list exported to {file_path}")
        return {"FINISHED"}


class FKtoIK_PropsGroup(bpy.types.PropertyGroup):
    mapping_preset: bpy.props.EnumProperty(name="Mapping Preset", items=[("new", "new preset", "New preset")])  # type: ignore
    src_armature: bpy.props.PointerProperty(type=bpy.types.Object, poll=lambda self, obj: obj.type == "ARMATURE")  # type: ignore
    # dst_armature: bpy.props.PointerProperty(type=bpy.types.Object, poll=lambda self, obj: obj.type == "ARMATURE")  # type: ignore
    is_current_selected: bpy.props.BoolProperty(name="Use Current Selected", default=True, description="Refresh bone list with current selected armature")  # type: ignore
    bone_list: bpy.props.CollectionProperty(type=BoneListItem)  # type: ignore
    bone_list_index: bpy.props.IntProperty()  # type: ignore
    frame_start: bpy.props.IntProperty(name="Frame Start", default=1)  # type: ignore
    frame_end: bpy.props.IntProperty(name="Frame End", default=250)  # type: ignore
    is_copy_scale: bpy.props.BoolProperty(name="Copy Scale", default=True, description="If true, the constraint would be `COPY_TRANSFORMS`, else `COPY_LOCATION`+`COPY_ROTATION`")  # type: ignore
    bone_layer_fallback: bpy.props.StringProperty(name="Bone Layer Fallback", default="IK")  # type: ignore


CLASS = [
    BoneListItem,
    FKtoIK_PropsGroup,
    FKtoIKOperator,
    FK_append_to_IK_Operator,
    OBJECT_OT_BoneListGetCurrent,
    OBJECT_OT_BoneListAdd,
    OBJECT_OT_BoneListRemove,
    OBJECT_OT_BoneListExport,
    BONE_UL_items,
]
CLASS_UI = [
    FKtoIKPanel,
]


def when_selected_update():
    """If this func not execute any once, re-enable this extension!"""
    props = bpy.context.scene.FKtoIK_props  # type: ignore
    active = bpy.context.active_object
    if props.is_current_selected and active and active.type == "ARMATURE":
        props.src_armature = active


@bpy.app.handlers.persistent
def register_msgbus(scene=None):
    bpy.msgbus.clear_by_owner(OWNER)
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.LayerObjects, "active"),  # type: ignore
        owner=OWNER,
        args=(),
        notify=when_selected_update,
    )


def register():
    [bpy.utils.register_class(cls) for cls in CLASS]
    bpy.types.Scene.FKtoIK_props = bpy.props.PointerProperty(type=FKtoIK_PropsGroup)  # type: ignore
    [bpy.utils.register_class(cls) for cls in CLASS_UI]
    bpy.app.handlers.load_post.append(register_msgbus)


def unregister():
    bpy.msgbus.clear_by_owner(OWNER)
    try:
        bpy.app.handlers.load_post.remove(register_msgbus)
    except Exception as e:
        Log.error("", exc_info=e)
    [bpy.utils.unregister_class(cls) for cls in reversed(CLASS_UI)]
    del bpy.types.Scene.FKtoIK_props  # type: ignore
    [bpy.utils.unregister_class(cls) for cls in reversed(CLASS)]


if __name__ == "__main__":
    register()
