import bpy, math
from mathutils import Vector
scene = bpy.context.scene
head = bpy.data.objects["MetaHumanHead_Textured"]; me = head.data; sk = me.shape_keys
eyeR = bpy.data.objects["Eyeball"]; eyeL = bpy.data.objects["Eyeball_L"]
def bag(ad): return ad.action.layers[0].strips[0].channelbag(ad.action_slot)
def rem_drivers(idb, path_contains):
    if idb.animation_data:
        for fc in list(idb.animation_data.drivers):
            if path_contains in fc.data_path: idb.animation_data.drivers.remove(fc)
def add_driver(idb, path, expr, vars_, index=-1):
    fc = idb.driver_add(path, index) if index >= 0 else idb.driver_add(path); fc.driver.type='SCRIPTED'
    for name, (idt, idv, dp) in vars_.items():
        v = fc.driver.variables.new(); v.name = name; v.targets[0].id_type = idt; v.targets[0].id = idv; v.targets[0].data_path = dp
    fc.driver.expression = expr; return fc

# ---------- STEP 2: EyeCtrl
ctrl = bpy.data.objects.get("EyeCtrl") or bpy.data.objects.new("EyeCtrl", None)
if ctrl.name not in scene.collection.objects and not ctrl.users_collection: scene.collection.objects.link(ctrl)
ctrl.empty_display_type = 'CIRCLE'; ctrl.empty_display_size = 0.03
CR = sum((eyeR.matrix_world @ Vector(c) for c in eyeR.bound_box), Vector())/8
front = (bpy.data.objects["hero_socket"].matrix_world.translation - CR); front.z = 0; front.normalize()
ctrl.location = Vector((0, CR.y, CR.z)) + front*0.12
for prop, val, lo, hi, desc in (("blink",0.0,0.0,1.0,"0 auki – 1 kiinni (molemmat luomet)"),("pupil",0.75,0.0,1.0,"pupillin laajuus"),
                               ("look_x",0.0,-1.0,1.0,"katse vasen–oikea"),("look_y",0.0,-1.0,1.0,"katse alas–ylös"),("fuzz",1,0,1,"untuvakarvat renderissä 1/0")):
    ctrl[prop] = val
    ui = ctrl.id_properties_ui(prop); ui.update(min=lo, max=hi, soft_min=lo, soft_max=hi, description=desc)
# blink-demo keyframet ohjaimelle, keyt pois shape keyltä, driverit tilalle
kbR = sk.key_blocks["blink_close"]; kbL = sk.key_blocks["blink_close_L"]
if sk.animation_data and sk.animation_data.action:
    b = bag(sk.animation_data)
    for fc in list(b.fcurves):
        if fc.data_path == 'key_blocks["blink_close"].value':
            for kp in fc.keyframe_points:
                ctrl["blink"] = float(kp.co.y); ctrl.keyframe_insert('["blink"]', frame=int(kp.co.x))
            cb = bag(ctrl.animation_data)
            for fc2 in cb.fcurves:
                if fc2.data_path == '["blink"]':
                    for kp2, kp in zip(sorted(fc2.keyframe_points, key=lambda k:k.co.x), sorted(fc.keyframe_points, key=lambda k:k.co.x)):
                        kp2.interpolation = kp.interpolation; kp2.easing = kp.easing
                    fc2.update()
            b.fcurves.remove(fc); print("blink-demo siirretty EyeCtrl.blink:iin")
rem_drivers(sk, 'blink_close_L')
add_driver(kbR, "value", "b", {"b": ('OBJECT', ctrl, '["blink"]')})
add_driver(kbL, "value", "b", {"b": ('OBJECT', ctrl, '["blink"]')})
# pupilli molempiin silmiin
for k in bpy.data.shape_keys:
    if "Dilation" in [x.name for x in k.key_blocks]:
        if k.animation_data:
            for fc in list(bag(k.animation_data).fcurves):
                if "Dilation" in fc.data_path: bag(k.animation_data).fcurves.remove(fc)
        add_driver(k.key_blocks["Dilation"], "value", "p", {"p": ('OBJECT', ctrl, '["pupil"]')})
# katse: DAMPED_TRACK eye_aimiin, saccade-keyt pois, eye_aim_L seuraa
aimR = bpy.data.objects.get("eye_aim"); aimL = bpy.data.objects.get("eye_aim_L")
for eye in (eyeR, eyeL):
    if eye.animation_data and eye.animation_data.action:
        for fc in list(bag(eye.animation_data).fcurves):
            if fc.data_path == "rotation_euler": bag(eye.animation_data).fcurves.remove(fc)
    for c in list(eye.constraints):
        if c.type in ('TRACK_TO','DAMPED_TRACK'): eye.constraints.remove(c)
if aimR:
    cR = eyeR.constraints.new('DAMPED_TRACK'); cR.target = aimR; cR.track_axis = 'TRACK_NEGATIVE_Y' if False else 'TRACK_Y'
    if not aimL: aimL = bpy.data.objects.new("eye_aim_L", None); scene.collection.objects.link(aimL)
    aimL.constraints.clear() if hasattr(aimL.constraints, "clear") else None
    for c in list(aimL.constraints): aimL.constraints.remove(c)
    cl = aimL.constraints.new('COPY_LOCATION'); cl.target = aimR
    cL = eyeL.constraints.new('DAMPED_TRACK'); cL.target = aimL; cL.track_axis = cR.track_axis
    # look_x/look_y -> eye_aim delta
    rem_drivers(aimR, "delta_location")
    add_driver(aimR, "delta_location", "lx*0.05", {"lx": ('OBJECT', ctrl, '["look_x"]')}, index=0)
    fz = aimR.driver_add("delta_location", 2); fz.driver.type='SCRIPTED'
    v = fz.driver.variables.new(); v.name="ly"; v.targets[0].id_type='OBJECT'; v.targets[0].id=ctrl; v.targets[0].data_path='["look_y"]'; fz.driver.expression="ly*0.035"
    # pieni demo-katsedrift ohjaimeen
    ctrl["look_x"] = 0.0; ctrl.keyframe_insert('["look_x"]', frame=1); ctrl["look_x"] = 0.25; ctrl.keyframe_insert('["look_x"]', frame=60); ctrl["look_x"] = -0.15; ctrl.keyframe_insert('["look_x"]', frame=112)
    print("katse: DAMPED_TRACK molemmissa, ohjain look_x/look_y")
else:
    print("eye_aim puuttuu – katse jätetty")

# ---------- STEP 5: fuzz-kytkin
pm = next((m for m in head.modifiers if m.type == 'PARTICLE_SYSTEM'), None)
if pm:
    for path in ("show_render", "show_viewport"):
        add_driver(pm, path, "f > 0.5", {"f": ('OBJECT', ctrl, '["fuzz"]')})
    # ---------- STEP 6: untuvakarvat koko kasvoille
    vg = head.vertex_groups.get("fuzz_zone") or head.vertex_groups.new(name="fuzz_zone")
    lidR = head.vertex_groups.get("lid_deform"); lidL = head.vertex_groups.get("lid_deform_L")
    mw3 = head.matrix_world.to_3x3()
    for v in me.vertices:
        n = (mw3 @ v.normal).normalized(); wz = (head.matrix_world @ v.co).z
        w = 0.0
        if n.dot(front) > 0.15 and wz > CR.z - 0.13: w = 1.0
        vg.add([v.index], w, 'REPLACE')
    pm.particle_system.settings.count = 45000
    print("fuzz: koko kasvot, 45k")

# ---------- STEP 3: kokoelmat
root = bpy.data.collections.get("EyeFace") or bpy.data.collections.new("EyeFace")
if root.name not in [c.name for c in scene.collection.children]: scene.collection.children.link(root)
subs = {}
for nm in ("HEAD","EYES","LASHES","RIG","FX","LIGHTS_XO","LIGHTS_Studio","CAMERAS"):
    c = bpy.data.collections.get(nm) or bpy.data.collections.new(nm)
    if c.name not in [x.name for x in root.children]: root.children.link(c)
    subs[nm] = c
def place(o, nm):
    for c in list(o.users_collection): c.objects.unlink(o)
    subs[nm].objects.link(o)
for o in list(bpy.data.objects):
    n = o.name
    if o.type == 'CAMERA': place(o, "CAMERAS")
    elif o.type == 'LIGHT': place(o, "LIGHTS_XO")
    elif n.startswith(("lashes","eyebrow")): place(o, "LASHES")
    elif n.startswith(("lash_pivot","EyeCtrl","eye_aim")): place(o, "RIG")
    elif n.startswith(("TearLine","reflect_pitch")): place(o, "FX")
    elif n == "MetaHumanHead_Textured": place(o, "HEAD")
    else: place(o, "EYES")
for c in list(bpy.data.collections):
    if c.name not in subs and c.name != "EyeFace" and len(c.objects) == 0 and len(c.children) == 0: bpy.data.collections.remove(c)
# ---------- STEP 4: studiovalot (pois päältä oletuksena)
def light(nm, pos, energy, size, color):
    ld = bpy.data.lights.new(nm, 'AREA'); ld.energy = energy; ld.size = size; ld.color = color
    lo = bpy.data.objects.new(nm, ld); subs["LIGHTS_Studio"].objects.link(lo); lo.location = pos
    lo.rotation_euler = (CR - Vector(pos)).normalized().to_track_quat('-Z','Y').to_euler()
side = front.cross(Vector((0,0,1))).normalized()
light("Studio_Key", CR + front*0.5 - side*0.35 + Vector((0,0,0.3)), 60, 0.4, (1.0,0.96,0.92))
light("Studio_Fill", CR + front*0.45 + side*0.4 + Vector((0,0,0.05)), 18, 0.6, (0.9,0.95,1.0))
light("Studio_Rim", CR - front*0.2 + side*0.45 + Vector((0,0,0.35)), 40, 0.25, (1.0,1.0,1.0))
vl = scene.view_layers[0]
def find_lc(lc, name):
    if lc.collection.name == name: return lc
    for ch in lc.children:
        r = find_lc(ch, name)
        if r: return r
lcs = find_lc(vl.layer_collection, "LIGHTS_Studio")
if lcs: lcs.exclude = True
# asset-merkintä
root.asset_mark()
try:
    with bpy.context.temp_override(id=root):
        bpy.ops.ed.lib_id_load_custom_preview(filepath="/Users/mikkonurminen/Desktop/3D BLENDER/eye-face-asset/probe_step1_open.png")
    print("asset-preview ladattu")
except Exception as e: print("preview:", e)
# kulmakarva_L kiinni ihoon
eb = bpy.data.objects.get("eyebrow_L")
if eb and not any(m.type == 'SHRINKWRAP' for m in eb.modifiers):
    sw = eb.modifiers.new("SkinContact", 'SHRINKWRAP'); sw.target = head; sw.offset = 0.0006; sw.wrap_method = 'NEAREST_SURFACEPOINT'
print("kokoelmat:", [c.name for c in root.children], "| valot XO:", len(subs["LIGHTS_XO"].objects), "studio:", len(subs["LIGHTS_Studio"].objects))
bpy.ops.wm.save_mainfile(); print("STEP2-6 OK")
