import bpy, math
from mathutils import Vector, Matrix, kdtree
scene = bpy.context.scene
head = bpy.data.objects["MetaHumanHead_Textured"]; me = head.data; mw = head.matrix_world; inv = mw.inverted()
eyeR = bpy.data.objects["Eyeball"]
CR = sum((eyeR.matrix_world @ Vector(c) for c in eyeR.bound_box), Vector())/8; R = max(eyeR.dimensions)/2
CL = Vector((-CR.x, CR.y, CR.z))
MIR = Matrix.Scale(-1, 4, Vector((1,0,0)))
root = eyeR
while root.parent: root = root.parent
def copy_hier(src, parent=None, suffix="_L"):
    c = src.copy()
    if src.data and src.type != 'EMPTY': c.data = src.data.copy()
    c.name = src.name + suffix
    for col in src.users_collection: col.objects.link(c)
    c.parent = parent
    if parent is not None: c.matrix_parent_inverse = src.matrix_parent_inverse.copy()
    for ch in src.children: copy_hier(ch, c, suffix)
    return c
rootL = copy_hier(root); rootL.matrix_world = Matrix.Translation(CL - CR) @ root.matrix_world
eyeL = bpy.data.objects["Eyeball_L"]
# --- peilattu siirtymäkenttä KD-puulla
sk = me.shape_keys; basis = sk.key_blocks["Basis"]; kbR = sk.key_blocks["blink_close"]; arcR = sk.key_blocks["blink_arc"]
n = len(me.vertices)
kd = kdtree.KDTree(n)
for i in range(n): kd.insert(mw @ basis.data[i].co, i)
kd.balance()
kbL = head.shape_key_add(name="blink_close_L", from_mix=False); arcL = head.shape_key_add(name="blink_arc_L", from_mix=False)
for i in range(n): kbL.data[i].co = basis.data[i].co; arcL.data[i].co = basis.data[i].co
moved, far = 0, 0
for i in range(n):
    d = kbR.data[i].co - basis.data[i].co
    if d.length < 1e-6: continue
    wpos = mw @ basis.data[i].co
    mpos = Vector((-wpos.x, wpos.y, wpos.z))
    co, j, dist = kd.find(mpos)
    if dist > 0.0025: far += 1; continue
    dw = mw.to_3x3() @ d; dwm = Vector((-dw.x, dw.y, dw.z)); dl = inv.to_3x3() @ dwm
    kbL.data[j].co = basis.data[j].co + dl
    da = arcR.data[i].co - basis.data[i].co; daw = mw.to_3x3() @ da; dam = Vector((-daw.x, daw.y, daw.z))
    arcL.data[j].co = basis.data[j].co + (inv.to_3x3() @ dam)
    moved += 1
print(f"peilattu key: {moved} verteksiä, {far} ilman vastinetta (>2.5 mm)")
fcd = arcL.driver_add("value"); fcd.driver.type='SCRIPTED'
var = fcd.driver.variables.new(); var.name="bc"; var.targets[0].id_type='KEY'; var.targets[0].id=sk
var.targets[0].data_path='key_blocks["blink_close_L"].value'; fcd.driver.expression="4*bc*(1-bc)"
g_def = head.vertex_groups.new(name="lid_deform_L"); g_con = head.vertex_groups.new(name="lid_contact_L")
disp = [(kbL.data[i].co - basis.data[i].co).length for i in range(n)]; dmax = max(disp)
for i, d in enumerate(disp):
    if d > 1e-6:
        w = min(1.0, d/(0.35*dmax)); w = w*w*(3-2*w); g_def.add([i], w, 'REPLACE')
        rr = ((mw @ kbL.data[i].co) - CL).length
        if rr < 1.35*R: g_con.add([i], max(0.0, min(1.0, (1.35*R-rr)/(0.25*R)))*w, 'REPLACE')
relax = head.modifiers.new("LidRelax_L", 'CORRECTIVE_SMOOTH'); relax.factor=0.6; relax.iterations=30
relax.smooth_type='LENGTH_WEIGHTED'; relax.vertex_group="lid_deform_L"; relax.use_only_smooth=True
wrap = head.modifiers.new("LidContact_L", 'SHRINKWRAP'); wrap.target=eyeL; wrap.wrap_method='NEAREST_SURFACEPOINT'; wrap.offset=0.0009; wrap.vertex_group="lid_contact_L"
bpy.context.view_layer.objects.active = head
bpy.ops.object.modifier_move_to_index(modifier="LidRelax_L", index=2); bpy.ops.object.modifier_move_to_index(modifier="LidContact_L", index=3)
def retarget(o):
    if o.animation_data:
        for fc in o.animation_data.drivers:
            for v in fc.driver.variables:
                for tg in v.targets:
                    if tg.data_path and 'blink_close"' in tg.data_path: tg.data_path = tg.data_path.replace('blink_close"', 'blink_close_L"')
retarget(eyeL)
def mirror_copy(name, newname):
    o = bpy.data.objects[name]; c = o.copy()
    if o.data: c.data = o.data.copy()
    c.name = newname
    for col in o.users_collection: col.objects.link(c)
    c.matrix_world = MIR @ o.matrix_world
    return c
pivL = mirror_copy("lash_pivot", "lash_pivot_L"); pivLL = mirror_copy("lash_pivot_lower", "lash_pivot_lower_L")
retarget(pivL); retarget(pivLL)
for src, dst, piv in (("lashes_upper","lashes_upper_L",pivL), ("lashes_lower","lashes_lower_L",pivLL)):
    c = mirror_copy(src, dst)
    for con in list(c.constraints): c.constraints.remove(con)
    con = c.constraints.new('CHILD_OF'); con.target = piv; con.inverse_matrix = piv.matrix_world.inverted()
for src, dst in (("eyebrow","eyebrow_L"), ("TearLine","TearLine_L")):
    if bpy.data.objects.get(src): mirror_copy(src, dst)
# blink_close_L seuraa blink_closea (kunnes EyeCtrl vaiheessa 2)
fcd = kbL.driver_add("value"); fcd.driver.type='SCRIPTED'
var = fcd.driver.variables.new(); var.name="b"; var.targets[0].id_type='KEY'; var.targets[0].id=sk
var.targets[0].data_path='key_blocks["blink_close"].value'; fcd.driver.expression="b"
bpy.ops.wm.save_as_mainfile(filepath="/Users/mikkonurminen/Desktop/3D BLENDER/eye-face-asset/eye_face_asset.blend", compress=True)
# --- todennus edestä
cam = bpy.data.objects["CAM_face"]; scene.camera = cam
scene.render.resolution_x = 1080; scene.render.resolution_y = 1080; scene.render.resolution_percentage = 50; scene.cycles.samples = 48
prefs = bpy.context.preferences.addons["cycles"].preferences; prefs.compute_device_type='METAL'; prefs.refresh_devices()
for d_ in prefs.devices: d_.use = True
scene.cycles.device = 'GPU'
for f, nm in ((40, "step1_open"), (1, "step1_closed")):
    scene.frame_set(f); scene.render.filepath = f"/Users/mikkonurminen/Desktop/3D BLENDER/eye-face-asset/probe_{nm}.png"; bpy.ops.render.render(write_still=True)
print("STEP1B OK")
