# Katse-rigi + silmäkuopan korjaukset (ajettu tässä järjestyksessä step 05/06:n jälkeen).
# Löydökset: iiris on silmämunan LOKAALI +Z (ei +Y) -> DAMPED_TRACK TRACK_Z; skannin molemmat silmäkuopat ovat avoimia reikiä
#  pään sisään ja luomiaukko on sarveiskalvon edessä -> silmät 1,5 mm eteen + sidekalvokaista (fornix) luomen reunasta taaksepäin.
# Vain referenssiksi; assetissa nämä on jo tehty.

# ================= fix_gaze.py
import bpy
from mathutils import Vector
scene = bpy.context.scene
eyeR = bpy.data.objects["Eyeball"]; eyeL = bpy.data.objects["Eyeball_L"]
cR = sum((eyeR.matrix_world @ Vector(v) for v in eyeR.bound_box), Vector())/8
cL = sum((eyeL.matrix_world @ Vector(v) for v in eyeL.bound_box), Vector())/8
mid = (cR + cL)/2
front = (bpy.data.objects["hero_socket"].matrix_world.translation - cR); front.z = 0; front.normalize()
aim = bpy.data.objects["eye_aim"]
if aim.animation_data and aim.animation_data.action:
    bag = aim.animation_data.action.layers[0].strips[0].channelbag(aim.animation_data.action_slot)
    for fc in list(bag.fcurves): bag.fcurves.remove(fc)
aim.parent = None
aim.location = mid + front * 1.0
for fc in aim.animation_data.drivers:
    if fc.data_path == "delta_location":
        fc.driver.expression = "lx*0.25" if fc.array_index == 0 else "ly*0.18"
print("eye_aim ->", tuple(round(v,3) for v in aim.location), "(1 m edessä)")
bpy.ops.wm.save_mainfile()

# ================= fix_track.py
import bpy
from mathutils import Vector
scene = bpy.context.scene
def cornea_dir(eye):
    cor = next(c for c in eye.children if "Cornea" in c.name)
    cen = sum((cor.matrix_world @ v.co for v in cor.data.vertices), Vector())/len(cor.data.vertices)
    loc = eye.matrix_world.inverted() @ cen
    return loc.normalized()
for name in ("Eyeball","Eyeball_L"):
    eye = bpy.data.objects[name]
    # constraint off first to get rest orientation
    con = next(k for k in eye.constraints if k.type=='DAMPED_TRACK')
    con.mute = True
    bpy.context.view_layer.update()
    d = cornea_dir(eye)
    axes = {'TRACK_X':Vector((1,0,0)),'TRACK_NEGATIVE_X':Vector((-1,0,0)),'TRACK_Y':Vector((0,1,0)),
            'TRACK_NEGATIVE_Y':Vector((0,-1,0)),'TRACK_Z':Vector((0,0,1)),'TRACK_NEGATIVE_Z':Vector((0,0,-1))}
    best = max(axes, key=lambda k: axes[k].dot(d))
    con.track_axis = best
    con.mute = False
    print(name, "cornea local dir", tuple(round(x,2) for x in d), "->", best)
bpy.ops.wm.save_mainfile()
print("SAVED")

# ================= fix_bell.py
import bpy, time
scene = bpy.context.scene
ctrl = bpy.data.objects["EyeCtrl"]
for name in ("Eyeball","Eyeball_L"):
    ob = bpy.data.objects[name]
    ad = ob.animation_data
    if ad:
        for fc in list(ad.drivers):
            print(name, "driver", fc.data_path, fc.array_index, fc.driver.expression)
            if fc.data_path == "delta_rotation_euler":
                ad.drivers.remove(fc); print("  removed (Bell now via eye_aim)")
aim = bpy.data.objects["eye_aim"]
for fc in aim.animation_data.drivers:
    if fc.data_path == "delta_location" and fc.array_index == 2:
        d = fc.driver
        if not any(v.name == "bl" for v in d.variables):
            v = d.variables.new(); v.name = "bl"; v.type = 'SINGLE_PROP'
            v.targets[0].id = ctrl; v.targets[0].data_path = '["blink"]'
        d.expression = "ly*0.18 + bl*0.22"
        print("eye_aim z driver:", d.expression, [(v.name, v.targets[0].data_path) for v in d.variables])
print("EyeCtrl props", {k: ctrl[k] for k in ctrl.keys() if not k.startswith('_')})
bpy.ops.wm.save_mainfile()
# timing: one hero_socket frame at demo res

# ================= fix_camtarget.py
import bpy, time
from mathutils import Vector
scene = bpy.context.scene
aim = bpy.data.objects["eye_aim"]
rig = bpy.data.collections["RIG"]
ct = bpy.data.objects.get("cam_target")
if not ct:
    ct = bpy.data.objects.new("cam_target", None); ct.empty_display_type = 'SPHERE'; ct.empty_display_size = 0.01
    rig.objects.link(ct)
ct.location = Vector((-0.023, -0.109, 0.231))   # alkuperäinen eye_aim-paikka (sarveiskalvon edessä)
keep = {"Eyeball", "Eyeball_L", "eye_aim_L"}
for ob in bpy.data.objects:
    for con in ob.constraints:
        if getattr(con, "target", None) == aim:
            if ob.name in keep: print("keep", ob.name, con.type)
            else: con.target = ct; print("retarget", ob.name, con.type, "-> cam_target")
    if ob.type == 'CAMERA' and ob.data.dof.focus_object == aim:
        ob.data.dof.focus_object = ct; print("dof", ob.name, "-> cam_target")
    ad = ob.animation_data
    if ad:
        for fc in ad.drivers:
            for v in fc.driver.variables:
                for t in v.targets:
                    if t.id == aim: print("DRIVER ref eye_aim:", ob.name, fc.data_path, v.name)
for nm in ("Studio_Key","Studio_Fill","Studio_Rim"):
    print(nm, "location", tuple(round(x,3) for x in bpy.data.objects[nm].location))
bpy.ops.wm.save_mainfile(); print("SAVED")

# ================= fix_studio.py
import bpy
for nm, e in (("Studio_Key", 24), ("Studio_Fill", 7), ("Studio_Rim", 16)):
    bpy.data.objects[nm].data.energy = e
bpy.ops.wm.save_mainfile(); print("STUDIO ENERGIES SAVED")

# ================= fix_lidL.py
import bpy
from mathutils import Vector, kdtree
scene = bpy.context.scene
head = bpy.data.objects["MetaHumanHead_Textured"]; me = head.data; mw = head.matrix_world
eR = bpy.data.objects["Eyeball"]; eL = bpy.data.objects["Eyeball_L"]
CR = sum((eR.matrix_world @ Vector(v) for v in eR.bound_box), Vector())/8
CL = sum((eL.matrix_world @ Vector(v) for v in eL.bound_box), Vector())/8
xm = (CR.x + CL.x)/2
basis = me.shape_keys.key_blocks["Basis"]
n = len(me.vertices)
kd = kdtree.KDTree(n)
for i in range(n): kd.insert(mw @ basis.data[i].co, i)
kd.balance()
def gweights(name):
    gi = head.vertex_groups[name].index; out = {}
    for v in me.vertices:
        for g in v.groups:
            if g.group == gi and g.weight > 0.001: out[v.index] = g.weight
    return out
conR = gweights("lid_contact"); defR = gweights("lid_deform")
gc = head.vertex_groups["lid_contact_L"]; gd = head.vertex_groups["lid_deform_L"]
gc.remove(list(range(n)))
dists = []; added_def = 0
for i, w in conR.items():
    p = mw @ basis.data[i].co; mp = Vector((2*xm - p.x, p.y, p.z))
    co, j, dist = kd.find(mp); dists.append(dist)
    gc.add([j], w, 'REPLACE')
    if j not in gweights("lid_deform_L"):
        gd.add([j], max(defR.get(i, 0.5), 0.5), 'REPLACE'); added_def += 1
print(f"lid_contact_L rebuilt: {len(conR)} verts, match dist mean {sum(dists)/len(dists)*1000:.2f} mm max {max(dists)*1000:.2f} mm, deform added {added_def}")
bpy.ops.wm.save_mainfile(); print("SAVED")

# ================= fix_conjunctiva.py
# Peruuta drape; anna kuopan seinämille sidekalvomateriaali (tumma vaaleanpunainen, kostea) mustan sijaan
import bpy, bmesh
from mathutils import Vector
scene = bpy.context.scene; scene.frame_set(40)
head = bpy.data.objects["MetaHumanHead_Textured"]; me = head.data; mw = head.matrix_world
# --- A: revert drape
for mod_name, eye_name, grp in (("LidContact","Eyeball","lid_contact"),("LidContact_L","Eyeball_L","lid_contact_L")):
    m = head.modifiers[mod_name]; m.target = bpy.data.objects[eye_name]; m.vertex_group = grp; m.offset = 0.0009
for nm in ("EyeShell","EyeShell_L"):
    o = bpy.data.objects.get(nm)
    if o: bpy.data.objects.remove(o, do_unlink=True)
for nm in ("lid_drape","lid_drape_L"):
    if nm in head.vertex_groups: head.vertex_groups.remove(head.vertex_groups[nm])
print("drape reverted")
# --- B: cavity walls
eR = bpy.data.objects["Eyeball"]; eL = bpy.data.objects["Eyeball_L"]
CR = sum((eR.matrix_world @ Vector(v) for v in eR.bound_box), Vector())/8; CL = sum((eL.matrix_world @ Vector(v) for v in eL.bound_box), Vector())/8
bm = bmesh.new(); bm.from_mesh(me)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
for side, c in (("R", CR), ("L", CL)):
    bnd = [e for e in bm.edges if e.is_boundary and all(((mw @ v.co) - c).length < 0.022 for v in e.verts)]
    print(side, "boundary edges near eye:", len(bnd))
mat = bpy.data.materials.get("Conjunctiva")
if not mat:
    mat = bpy.data.materials.new("Conjunctiva"); mat.use_nodes = True
    nt = mat.node_tree; p = nt.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (0.62, 0.24, 0.22, 1)
    p.inputs["Roughness"].default_value = 0.28
    p.inputs["Coat Weight"].default_value = 0.35
    p.inputs["Subsurface Weight"].default_value = 0.4
    p.inputs["Subsurface Radius"].default_value = (1.0, 0.3, 0.15)
    p.inputs["Subsurface Scale"].default_value = 0.004
    p.inputs["Emission Color"].default_value = (0.5, 0.14, 0.11, 1)
    p.inputs["Emission Strength"].default_value = 0.12
if mat.name not in [m.name for m in me.materials if m]: me.materials.append(mat)
slot = [i for i, m in enumerate(me.materials) if m and m.name == mat.name][0]
counts = {}
for side, c in (("R", CR), ("L", CL)):
    n = 0
    for f in bm.faces:
        cen = mw @ f.calc_center_median()
        r = cen - c
        if r.length > 0.021: continue
        nrm = (mw.to_3x3() @ f.normal).normalized()
        if nrm.dot(r) < -0.15 * r.length:   # normaali osoittaa silmän keskustaa kohti
            f.material_index = slot; n += 1
    counts[side] = n
bm.to_mesh(me); bm.free(); me.update()
print("conjunctiva faces", counts, "slot", slot, "mats", [m.name for m in me.materials if m])
bpy.ops.wm.save_mainfile(); print("SAVED")

# ================= fix_eyedepth.py
# Silmämunat 1,5 mm eteenpäin (skannin luomiaukko on sarveiskalvon edessä) + suljetut shape keyt seuraavat painotetusti
import bpy
from mathutils import Vector, Matrix
scene = bpy.context.scene; scene.frame_set(40)
head = bpy.data.objects["MetaHumanHead_Textured"]; me = head.data; inv3 = head.matrix_world.to_3x3().inverted()
SHIFT = 0.0015
for root_name, keys, grp in (("Realistic Rigged Procedural Eye", ("blink_close","blink_arc"), "lid_deform"),
                             ("Realistic Rigged Procedural Eye_L", ("blink_close_L","blink_arc_L"), "lid_deform_L")):
    root = bpy.data.objects[root_name]
    fwd = (root.matrix_world.to_3x3() @ Vector((0,0,1))).normalized()
    root.matrix_world = Matrix.Translation(fwd * SHIFT) @ root.matrix_world
    dl = inv3 @ (fwd * SHIFT)
    gi = head.vertex_groups[grp].index
    n = 0
    for v in me.vertices:
        w = next((g.weight for g in v.groups if g.group == gi), 0.0)
        if w <= 0: continue
        for k in keys: me.shape_keys.key_blocks[k].data[v.index].co += dl * w
        n += 1
    print(root_name, "moved", tuple(round(x*1000,2) for x in fwd*SHIFT), "mm; shape verts shifted", n)
# sidekalvo vielä tummemmaksi, ei SSS:ää (ohut pinta hohtaa)
p = bpy.data.materials["Conjunctiva"].node_tree.nodes["Principled BSDF"]
p.inputs["Base Color"].default_value = (0.30, 0.09, 0.08, 1); p.inputs["Subsurface Weight"].default_value = 0.0; p.inputs["Coat Weight"].default_value = 0.25
bpy.ops.wm.save_mainfile(); print("SAVED")

# ================= fix_fornix2.py
# Sidekalvokaista v2: pursotus TAAKSEPÄIN silmän akselia pitkin (luomen sisäpinta), ei keskustaa kohti -> edestä näkymätön
import bpy, bmesh
from mathutils import Vector
scene = bpy.context.scene; scene.frame_set(40)
head = bpy.data.objects["MetaHumanHead_Textured"]; me = head.data; mw = head.matrix_world; inv = mw.inverted()
eR = bpy.data.objects["Eyeball"]; eL = bpy.data.objects["Eyeball_L"]
CR = sum((eR.matrix_world @ Vector(v) for v in eR.bound_box), Vector())/8; CL = sum((eL.matrix_world @ Vector(v) for v in eL.bound_box), Vector())/8
fwdR = (eR.parent.matrix_world.to_3x3() @ Vector((0,0,1))).normalized(); fwdL = (eL.parent.matrix_world.to_3x3() @ Vector((0,0,1))).normalized()
slot = [i for i, m in enumerate(me.materials) if m and m.name == "Conjunctiva"][0]
gi_def = {"R": head.vertex_groups["lid_deform"].index, "L": head.vertex_groups["lid_deform_L"].index}
L = 0.0065; sc = mw.to_scale().x
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
# poista vanha kaista (viimeiset 100 verteksiä)
old = [bm.verts[i] for i in range(17626, len(bm.verts))]
print("removing old strip verts", len(old))
bmesh.ops.delete(bm, geom=old, context='VERTS')
bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table()
shape_layers = [bm.verts.layers.shape[k] for k in bm.verts.layers.shape.keys()]
dl = bm.verts.layers.deform.verify()
made = {}
for side, c, fwd in (("R", CR, fwdR), ("L", CL, fwdL)):
    cl = inv @ c; back_l = (inv.to_3x3() @ (-fwd)).normalized()
    bnd = [e for e in bm.edges if e.is_boundary and all(((mw @ v.co) - c).length < 0.022 for v in e.verts)]
    adj = {}
    for e in bnd:
        for v in e.verts: adj.setdefault(v, []).append(e)
    start = bnd[0].verts[0]; loop = [start]; prev_e = None; cur = start
    while True:
        es = [e for e in adj[cur] if e is not prev_e]
        if not es: break
        e = es[0]; nxt = e.other_vert(cur)
        if nxt is start: break
        loop.append(nxt); prev_e = e; cur = nxt
        if len(loop) > 500: break
    closed = len(loop) == len(bnd)
    newv = {}
    for v in loop:
        d = (back_l + 0.25 * (cl - v.co).normalized()).normalized()
        nv = bm.verts.new(v.co + d * L / sc)
        for lay in shape_layers: nv[lay] = v[lay] + d * L / sc
        w = v[dl].get(gi_def[side], 0.0)
        if w > 0: nv[dl][gi_def[side]] = w
        newv[v] = nv
    nf = 0; m = len(loop)
    for i in range(m if closed else m - 1):
        a, b = loop[i], loop[(i + 1) % m]
        try: f = bm.faces.new((a, b, newv[b], newv[a]))
        except ValueError: continue
        cen = f.calc_center_median()
        if f.normal.dot(cl - cen) < 0: f.normal_flip()
        f.material_index = slot; f.smooth = True; nf += 1
    made[side] = (len(loop), closed, nf)
bm.to_mesh(me); bm.free(); me.update()
print("FORNIX2", made, "verts", len(me.vertices))
bpy.ops.wm.save_mainfile(); print("SAVED")

# ================= fix_conj_final.py
import bpy
p = bpy.data.materials["Conjunctiva"].node_tree.nodes["Principled BSDF"]
p.inputs["Base Color"].default_value = (0.42, 0.12, 0.10, 1)
p.inputs["Roughness"].default_value = 0.30
p.inputs["Coat Weight"].default_value = 0.3
p.inputs["Subsurface Weight"].default_value = 0.15
p.inputs["Subsurface Radius"].default_value = (1.0, 0.4, 0.25)
p.inputs["Subsurface Scale"].default_value = 0.001
p.inputs["Emission Color"].default_value = (0.42, 0.10, 0.08, 1)
p.inputs["Emission Strength"].default_value = 0.05
bpy.ops.wm.save_mainfile(); print("CONJ FINAL SAVED")
