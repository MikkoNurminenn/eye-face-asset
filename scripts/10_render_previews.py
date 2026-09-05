import bpy
scene = bpy.context.scene
p = bpy.data.materials["Conjunctiva"].node_tree.nodes["Principled BSDF"]; p.inputs["Emission Strength"].default_value = 0.03
for o in list(bpy.data.objects):
    if o.name.startswith("CAM_mirror"): bpy.data.objects.remove(o, do_unlink=True)
scene.camera = bpy.data.objects["hero_socket"]; scene.frame_set(40)
bpy.ops.wm.save_mainfile()
def find_lc(lc, name):
    if lc.collection.name == name: return lc
    for ch in lc.children:
        r = find_lc(ch, name)
        if r: return r
vl = scene.view_layers[0]
prefs = bpy.context.preferences.addons["cycles"].preferences; prefs.compute_device_type='METAL'; prefs.refresh_devices()
for d_ in prefs.devices: d_.use = True
scene.cycles.device = 'GPU'; scene.cycles.samples = 64; scene.cycles.use_denoising = True
OUT = "/Users/mikkonurminen/Desktop/3D BLENDER/eye-face-asset/"
scene.render.resolution_x, scene.render.resolution_y = 1080, 1920; scene.render.resolution_percentage = 50
for f, nm in ((40, "open"), (1, "closed")):
    scene.frame_set(f); scene.render.filepath = OUT + f"preview_{nm}.png"; bpy.ops.render.render(write_still=True)
find_lc(vl.layer_collection, "LIGHTS_Studio").exclude = False; find_lc(vl.layer_collection, "LIGHTS_XO").exclude = True
scene.camera = bpy.data.objects["CAM_face"]; scene.render.resolution_x = scene.render.resolution_y = 1080; scene.render.resolution_percentage = 60
scene.frame_set(40); scene.render.filepath = OUT + "preview_face_studio.png"; bpy.ops.render.render(write_still=True)
print("PREVIEWS DONE")
