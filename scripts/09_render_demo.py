# Demo-klipit READMEen. Ei tallenna tiedostoa (demo-avaimet vain muistissa).
# Blender -b eye_face_asset.blend -P render_demo.py -- macro | face
import bpy, sys
scene = bpy.context.scene
mode = sys.argv[-1]
prefs = bpy.context.preferences.addons["cycles"].preferences; prefs.compute_device_type='METAL'; prefs.refresh_devices()
for d_ in prefs.devices: d_.use = True
scene.cycles.device = 'GPU'; scene.cycles.use_denoising = True
scene.render.image_settings.file_format = 'PNG'
def find_lc(lc, name):
    if lc.collection.name == name: return lc
    for ch in lc.children:
        r = find_lc(ch, name)
        if r: return r
vl = scene.view_layers[0]
if mode == "macro":
    scene.camera = bpy.data.objects["hero_socket"]
    scene.render.resolution_x, scene.render.resolution_y = 1080, 1920
    scene.render.resolution_percentage = 33; scene.cycles.samples = 24
    scene.frame_start, scene.frame_end = 1, 112
    scene.render.filepath = "/Users/mikkonurminen/Desktop/3D BLENDER/eye-face-asset/demo_frames/macro_####"
else:
    find_lc(vl.layer_collection, "LIGHTS_Studio").exclude = False
    find_lc(vl.layer_collection, "LIGHTS_XO").exclude = True
    scene.camera = bpy.data.objects["CAM_face"]
    scene.render.resolution_x = scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 50; scene.cycles.samples = 32
    ctrl = bpy.data.objects["EyeCtrl"]
    # tyhjennä demo-avaimet muistissa ja kirjoita ohjainsekvenssi
    if ctrl.animation_data and ctrl.animation_data.action:
        bag = ctrl.animation_data.action.layers[0].strips[0].channelbag(ctrl.animation_data.action_slot)
        for fc in list(bag.fcurves): bag.fcurves.remove(fc)
    keys = {
        "blink":  [(1,0),(8,0),(13,1),(15,1),(22,0)],
        "look_x": [(1,0),(24,0),(38,-1),(52,1),(66,0)],
        "look_y": [(1,0),(66,0),(76,-0.8),(88,0.8),(100,0)],
        "pupil":  [(1,0.75),(100,0.75),(112,0.0),(126,1.0),(140,0.75)],
        "fuzz":   [(1,1),(140,1)],
    }
    for prop, ks in keys.items():
        for f, v in ks:
            ctrl[prop] = v; ctrl.keyframe_insert(f'["{prop}"]', frame=f)
    scene.frame_start, scene.frame_end = 1, 140
    scene.render.filepath = "/Users/mikkonurminen/Desktop/3D BLENDER/eye-face-asset/demo_frames/face_####"
bpy.ops.render.render(animation=True)
print("DEMO", mode, "DONE")
