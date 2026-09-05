import bpy, sys
from mathutils import Vector
scene = bpy.context.scene
eyeR = bpy.data.objects["Eyeball"]; eyeL = bpy.data.objects["Eyeball_L"]
c = (sum((eyeR.matrix_world @ Vector(v) for v in eyeR.bound_box), Vector())/8 + sum((eyeL.matrix_world @ Vector(v) for v in eyeL.bound_box), Vector())/8)/2
front = (bpy.data.objects["hero_socket"].matrix_world.translation - c); front.z = 0; front.normalize()
cam = bpy.data.objects.get("CAM_face")
if not cam:
    cd = bpy.data.cameras.new("CAM_face"); cd.lens = 70; cam = bpy.data.objects.new("CAM_face", cd); scene.collection.objects.link(cam)
cam.location = c + front*0.42 + Vector((0,0,0.01))
cam.rotation_euler = (c - cam.location).normalized().to_track_quat('-Z','Y').to_euler()
scene.camera = cam
scene.render.resolution_x = 1080; scene.render.resolution_y = 1080; scene.render.resolution_percentage = 50; scene.cycles.samples = 48
prefs = bpy.context.preferences.addons["cycles"].preferences; prefs.compute_device_type='METAL'; prefs.refresh_devices()
for d_ in prefs.devices: d_.use = True
scene.cycles.device = 'GPU'
tag = sys.argv[-1]
for f, nm in ((40, "open"), (1, "closed")):
    scene.frame_set(f); scene.render.filepath = f"/Users/mikkonurminen/Desktop/3D BLENDER/eye-face-asset/probe_{tag}_{nm}.png"; bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_mainfile(); print("RENDER OK", tag)
