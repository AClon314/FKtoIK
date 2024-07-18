bl_info = {
    "name": "FK to IK Bone Conversion",
    "blender": (4, 0, 0),
    "category": "Animation",
}

import bpy

def duplicate_bones(armature_name, bone_names):
    # Ensure Blender is in Object Mode
    bpy.ops.object.mode_set(mode='OBJECT')

    # Get the armature object
    armature = bpy.data.objects.get(armature_name)
    if not armature:
        print("[FKTOIK] Armature not found.")
        return

    # Make sure the armature is the active object
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)

    # Switch to Edit Mode
    bpy.ops.object.mode_set(mode='EDIT')

    dup_bone_names = []
    # Iterate through specified bones and duplicate them
    for bone_name in bone_names:
        if bone_name in armature.data.edit_bones:
            original_bone = armature.data.edit_bones[bone_name]
            # Create a new bone
            new_bone = armature.data.edit_bones.new(original_bone.name + ".001")
            dup_bone_names.append(new_bone.name)
            # Copy properties
            new_bone.length = original_bone.length
            new_bone.matrix = original_bone.matrix.copy()
        else:
            print(f"[FKTOIK] Bone named '{bone_name}' not found.")

    # Return to Object Mode
    bpy.ops.object.mode_set(mode='OBJECT')

    return dup_bone_names


def add_constraints(armature_name, bone_names, target_names):
    # Ensure we're in Object Mode
    bpy.ops.object.mode_set(mode='OBJECT')

    # Select the armature object
    armature = bpy.data.objects.get(armature_name)
    if not armature:
        print("[FKTOIK] Armature not found.")
        return
    
    # Set the armature as the active object
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)

    # Switch to Pose Mode
    bpy.ops.object.mode_set(mode='POSE')

    # Loop through all bones and their corresponding targets
    for bone_name, target_name in zip(bone_names, target_names):
        bone = armature.pose.bones.get(bone_name)
        if bone:
            # Add a copy location constraint
            copy_loc = bone.constraints.new('COPY_LOCATION')
            copy_loc.target = armature
            copy_loc.subtarget = target_name  # Target the original bone
            
            # Add a copy rotation constraint
            copy_rot = bone.constraints.new('COPY_ROTATION')
            copy_rot.target = armature
            copy_rot.subtarget = target_name  # Target the original bone
        else:
            print(f"[FKTOIK] Bone named '{bone_name}' not found in the armature.")

    # Return to Object Mode
    bpy.ops.object.mode_set(mode='OBJECT')


def bake_animation_to_keyframes(armature_name, bone_names, frame_start, frame_end):
    print("[FKTOIK] initiate baking")
    # Ensure Blender is in Object Mode
    bpy.ops.object.mode_set(mode='OBJECT')

    # Get the armature object
    armature = bpy.data.objects.get(armature_name)
    if not armature:
        print("[FKTOIK] Armature not found.")
        return

    # Make sure the armature is the active object
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)

    # Switch to Pose Mode
    bpy.ops.object.mode_set(mode='POSE')

    # Deselect all bones
    bpy.ops.pose.select_all(action='DESELECT')

    # Select the specific bones
    for bone_name in bone_names:
        bone = armature.pose.bones.get(bone_name)
        if bone:
            armature.data.bones[bone_name].select = True
        else:
            print(f"[FKTOIK] Bone named '{bone_name}' not found.")

    print("[FKTOIK] start bake command")
    # Bake the animation
    bpy.ops.nla.bake(frame_start=frame_start, frame_end=frame_end, only_selected=True, visual_keying=True, clear_constraints=True, clear_parents=False, use_current_action=True, bake_types={'POSE'})
    # Return to Object Mode
    bpy.ops.object.mode_set(mode='OBJECT')
    print("[FKTOIK] successfully bake")


def clear_bone_parents(armature_name, bone_names):
    # Ensure we're in Object Mode
    bpy.ops.object.mode_set(mode='OBJECT')

    # Get the armature object
    armature = bpy.data.objects.get(armature_name)
    if not armature:
        print("[FKTOIK] Armature not found.")
        return

    # Set the armature as the active object
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)

    # Switch to Edit Mode
    bpy.ops.object.mode_set(mode='EDIT')

    # Get the edit bones
    edit_bones = armature.data.edit_bones

    # Iterate through the specified bones and clear their parents
    for bone_name in bone_names:
        bone = edit_bones.get(bone_name)
        if bone:
            bone.parent = None
            print(f"[FKTOIK] Parent cleared for bone: {bone_name}")
        else:
            print(f"[FKTOIK] Bone named '{bone_name}' not found in the armature.")

    # Return to Object Mode
    bpy.ops.object.mode_set(mode='OBJECT')

def cleanup(armature_name, duplicated_bone_names):
    # Ensure Blender is in Object Mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Get the armature object
    armature = bpy.data.objects.get(armature_name)
    if not armature:
        print("[FKTOIK] Armature not found.")
        return
    
    # Set the armature as the active object
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    
    # Remove animation data associated with the bones
    if armature.animation_data and armature.animation_data.action:
        fcurves = armature.animation_data.action.fcurves
        for fcurve in fcurves:
            for bone_name in duplicated_bone_names:
                if fcurve.data_path.startswith("pose.bones[\"" + bone_name + "\"]"):
                    fcurves.remove(fcurve)
                    break  # Break the inner loop to avoid modifying the list during iteration
    
    # Switch to Edit Mode to remove bones
    bpy.ops.object.mode_set(mode='EDIT')
    for bone_name in duplicated_bone_names:
        bone = armature.data.edit_bones.get(bone_name)
        if bone:
            armature.data.edit_bones.remove(bone)
        else:
            print(f"[FKTOIK] Bone named '{bone_name}' not found.")
    
    # Return to Object Mode
    bpy.ops.object.mode_set(mode='OBJECT')



class FKtoIKOperator(bpy.types.Operator):
    "Convert FK Bones to IK"
    bl_idname = "object.convert_fk_to_ik"
    bl_label = "Convert FK to IK"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.my_armature is not None and context.scene.bone_name_1 and context.scene.bone_name_2

    def execute(self, context):
        
        VAR_armature_name = context.scene.my_armature.name
        VAR_bone_names = [context.scene.bone_name_1, context.scene.bone_name_2]
        VAR_dup_bone_names = duplicate_bones(VAR_armature_name, VAR_bone_names)
        print(f"[FKTOIK] BONES DUPLICATED: '{VAR_dup_bone_names}'")

        add_constraints(VAR_armature_name, VAR_dup_bone_names, VAR_bone_names)
        print("[FKTOIK] successfully added first constraints")

        bake_animation_to_keyframes(VAR_armature_name, VAR_dup_bone_names, bpy.context.scene.frame_start, bpy.context.scene.frame_end)

        clear_bone_parents(VAR_armature_name, VAR_bone_names)

        print("[FKTOIK] successfully cleared bone parents")

        add_constraints(VAR_armature_name, VAR_bone_names, VAR_dup_bone_names)

        print("[FKTOIK] successfully added second constraints")

        bake_animation_to_keyframes(VAR_armature_name, VAR_bone_names, bpy.context.scene.frame_start, bpy.context.scene.frame_end)

        cleanup(VAR_armature_name, VAR_dup_bone_names)

        print("[FKTOIK] duplicate bones cleaned up")
        print("[FKTOIK] TRANSFER FROM FK TO IK COMPLETE")
        return {'FINISHED'}

class FKtoIKPanel(bpy.types.Panel):
    bl_label = "FK to IK Conversion"
    bl_idname = "OBJECT_PT_fk_to_ik"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FK to IK'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.prop(scene, "my_armature", text="Armature")

        if scene.my_armature:
            layout.prop_search(scene, "bone_name_1", scene.my_armature.data, "bones", text="Bone 1")
            layout.prop_search(scene, "bone_name_2", scene.my_armature.data, "bones", text="Bone 2")

        layout.operator("object.convert_fk_to_ik")

def register():
    bpy.utils.register_class(FKtoIKOperator)
    bpy.utils.register_class(FKtoIKPanel)
    bpy.types.Scene.my_armature = bpy.props.PointerProperty(type=bpy.types.Object, poll=lambda self, obj: obj.type == 'ARMATURE')
    bpy.types.Scene.bone_name_1 = bpy.props.StringProperty()
    bpy.types.Scene.bone_name_2 = bpy.props.StringProperty()

def unregister():
    bpy.utils.unregister_class(FKtoIKOperator)
    bpy.utils.unregister_class(FKtoIKPanel)
    del bpy.types.Scene.my_armature
    del bpy.types.Scene.bone_name_1
    del bpy.types.Scene.bone_name_2

if __name__ == "__main__":
    register()