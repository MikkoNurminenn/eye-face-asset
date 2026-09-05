import bpy, math
from mathutils import Vector
scene = bpy.context.scene

eye = bpy.data.objects["Eyeball"]
pts = [eye.matrix_world @ Vector(c) for c in eye.bound_box]
lo = Vector(map(min, *pts)); hi = Vector(map(max, *pts))
C = (lo + hi) / 2
R = max(hi - lo) / 2

head = bpy.data.objects["MetaHumanHead_Textured"]
me = head.data
sk = me.shape_keys
kb = sk.key_blocks["blink_close"]
basis = sk.key_blocks["Basis"]
mw = head.matrix_world

# ---------- 1) ripsikorjaus: parent pois, CHILD_OF tilalle
for lname, pname in (("lashes_upper", "lash_pivot"),
                     ("lashes_lower", "lash_pivot_lower")):
    lash = bpy.data.objects[lname]
    piv = bpy.data.objects[pname]
    lash.parent = None
    for con in list(lash.constraints):
        lash.constraints.remove(con)
    con = lash.constraints.new('CHILD_OF')
    con.target = piv
    # inverse pivotin lepomatriisista (driver nollassa kun bc=0)
    con.inverse_matrix = piv.matrix_world.inverted()
    print(f"{lname}: CHILD_OF {pname}, inverse asetettu")

# ---------- 2) vertex-ryhmät solvereille
for gname in ("lid_deform", "lid_contact"):
    g = head.vertex_groups.get(gname)
    if g:
        head.vertex_groups.remove(g)
g_def = head.vertex_groups.new(name="lid_deform")
g_con = head.vertex_groups.new(name="lid_contact")
disp = [(kb.data[i].co - basis.data[i].co).length for i in range(len(me.vertices))]
dmax = max(disp)
n_def, n_con = 0, 0
for i, d in enumerate(disp):
    if d > 1e-6:
        w = min(1.0, d / (0.35 * dmax))
        w = w * w * (3 - 2 * w)
        g_def.add([i], w, 'REPLACE')
        n_def += 1
        # kontakti: suljettu sijainti lähellä munan pintaa
        rr = ((mw @ kb.data[i].co) - C).length
        if rr < 1.35 * R:
            wc = max(0.0, min(1.0, (1.35 * R - rr) / (0.25 * R)))
            g_con.add([i], wc * w, 'REPLACE')
            n_con += 1
print(f"lid_deform {n_def} v, lid_contact {n_con} v (dmax {dmax*1000:.1f} mm)")

# ---------- 3) solverit modifier-pinoon (ennen mahdollista subsurfia)
for mname in ("LidRelax", "LidContact"):
    m = head.modifiers.get(mname)
    if m:
        head.modifiers.remove(m)
print("nykyinen pino:", [(m.name, m.type) for m in head.modifiers])
relax = head.modifiers.new("LidRelax", 'CORRECTIVE_SMOOTH')
relax.factor = 0.6
relax.iterations = 30
relax.smooth_type = 'LENGTH_WEIGHTED'
relax.vertex_group = "lid_deform"
relax.use_only_smooth = True
wrap = head.modifiers.new("LidContact", 'SHRINKWRAP')
wrap.target = eye
wrap.wrap_method = 'NEAREST_SURFACEPOINT'
wrap.offset = 0.0009
wrap.vertex_group = "lid_contact"
# siirrä ylimmäksi järjestyksessä relax -> wrap
while head.modifiers.find("LidRelax") > 0:
    bpy.ops.object.modifier_move_up({"object": head}, modifier="LidRelax") if False else None
    break
# 5.2: käytä modifier_move_to_index
ctx = bpy.context.copy()
bpy.context.view_layer.objects.active = head
bpy.ops.object.modifier_move_to_index(modifier="LidRelax", index=0)
bpy.ops.object.modifier_move_to_index(modifier="LidContact", index=1)
print("solverit:", [(m.name, m.type) for m in head.modifiers][:4])
bpy.ops.wm.save_mainfile()

# ---------- 4) diagit
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = 'METAL'
prefs.refresh_devices()
for dv in prefs.devices:
    dv.use = True
scene.cycles.device = 'GPU'
scene.cycles.samples = 32
scene.render.resolution_percentage = 50
for f in (1, 8, 13):
    scene.frame_set(f)
    scene.render.filepath = f"/Users/mikkonurminen/Desktop/3D BLENDER/the-weekend/proof_sim_{f:03d}.png"
    bpy.ops.render.render(write_still=True)
    print(f"still fr{f} ok")
