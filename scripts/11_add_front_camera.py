import bpy
from mathutils import Vector
scene = bpy.context.scene
eR = bpy.data.objects["Eyeball"]; eL = bpy.data.objects["Eyeball_L"]
mid = (sum((eR.matrix_world @ Vector(v) for v in eR.bound_box), Vector())/8 + sum((eL.matrix_world @ Vector(v) for v in eL.bound_box), Vector())/8)/2
cams = bpy.data.collections["CAMERAS"]
cam = bpy.data.objects.get("CAM_front")
if not cam:
    cd = bpy.data.cameras.new("CAM_front"); cd.lens = 85; cam = bpy.data.objects.new("CAM_front", cd); cams.objects.link(cam)
cam.location = mid + Vector((0, -0.55, 0.01)); cam.rotation_euler = (mid - cam.location).normalized().to_track_quat('-Z','Y').to_euler()
cam.data.dof.use_dof = True; cam.data.dof.focus_object = bpy.data.objects["cam_target"]; cam.data.dof.aperture_fstop = 4.0
scene.camera = bpy.data.objects["hero_socket"]
bpy.ops.wm.save_mainfile(); print("CAM_front SAVED")
