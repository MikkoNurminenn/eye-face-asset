import bpy, math
from mathutils import Vector, Matrix
scene = bpy.context.scene

eye = bpy.data.objects["Eyeball"]
pts = [eye.matrix_world @ Vector(c) for c in eye.bound_box]
lo = Vector(map(min, *pts)); hi = Vector(map(max, *pts))
C = (lo + hi) / 2
R = max(hi - lo) / 2
cam = bpy.data.objects["hero_socket"]
scene.frame_set(30)
front = (cam.matrix_world.translation - C).normalized()
side = front.cross(Vector((0, 0, 1))).normalized() * -1
up = side.cross(front) * -1
if up.z < 0:
    up = -up; side = -side

head = bpy.data.objects["MetaHumanHead_Textured"]
me = head.data
sk = me.shape_keys
kb = sk.key_blocks["blink_close"]
basis = sk.key_blocks["Basis"]
mw = head.matrix_world
inv = mw.inverted()

def phi_of(p): return math.atan2(p.dot(up), p.dot(front))
low_margin = -1e9
for i in range(len(me.vertices)):
    p = (mw @ basis.data[i].co) - C
    if p.length < 1.25 * R and p.dot(front) > 0.15 * R and phi_of(p) < math.radians(-5):
        low_margin = max(low_margin, phi_of(p))
RISE = math.radians(6)
SEAM = low_margin + RISE + math.radians(3)
THETA = math.radians(80)
print(f"sauma {math.degrees(SEAM):.0f}°")

# --- blink_close v6: sisänurkka mukaan (kevennetty front-gate + side-fade)
# --- ja blink_arc: kaarikorjaus (arc-mid - chord-mid)
if "blink_arc" not in sk.key_blocks:
    arc = head.shape_key_add(name="blink_arc", from_mix=False)
else:
    arc = sk.key_blocks["blink_arc"]
n_in = 0
for i in range(len(me.vertices)):
    w_pos = mw @ basis.data[i].co
    p = w_pos - C
    r = p.length
    f = p.dot(front)
    s_abs = abs(p.dot(side))
    if r > 1.9 * R or f < -0.05 * R or s_abs > 1.7 * R:
        kb.data[i].co = basis.data[i].co
        arc.data[i].co = basis.data[i].co
        continue
    phi = phi_of(p)
    w_r = max(0.0, 1.0 - max(0.0, r - R) / (0.75 * R))
    w_r = w_r * w_r * (3 - 2 * w_r)
    w_s = max(0.0, min(1.0, (1.7 * R - s_abs) / (0.5 * R)))  # sisä/ulkonurkan fade
    w_gate = max(0.0, min(1.0, (f + 0.05 * R) / (0.2 * R)))   # pehmeä front-gate
    w = w_r * max(w_s, 0.35) * w_gate
    if phi > math.radians(-3):
        phi_new = max(phi - THETA * w, SEAM * min(1.0, w * 1.4) + phi * max(0.0, 1 - w * 1.4))
    else:
        phi_new = min(phi + RISE * w, SEAM - math.radians(2))
    ang = phi_new - phi
    p_closed = Matrix.Rotation(ang, 4, side) @ p
    du = p_closed.dot(up) - p.dot(up)
    if (ang < 0 and du > 0) or (ang > 0 and du < 0):
        p_closed = Matrix.Rotation(-ang, 4, side) @ p
    kb.data[i].co = inv @ (C + p_closed)
    # kaarikorjaus: puolikulman piste miinus jänteen keskipiste
    p_half_arc = Matrix.Rotation(ang * 0.5, 4, side) @ p
    chord_mid = (p + p_closed) * 0.5
    arc.data[i].co = inv @ (C + (p + (p_half_arc - chord_mid)))
    n_in += 1
print(f"key v6: {n_in} verteksiä, arc-korjaus mukana")

# --- blink_arc driver: 4*v*(1-v)
if arc.id_data.animation_data is None or True:
    try:
        arc.driver_remove("value")
    except Exception:
        pass
fcd = arc.driver_add("value")
fcd.driver.type = 'SCRIPTED'
var = fcd.driver.variables.new()
var.name = "bc"
var.targets[0].id_type = 'KEY'
var.targets[0].id = sk
var.targets[0].data_path = 'key_blocks["blink_close"].value'
fcd.driver.expression = "4*bc*(1-bc)"
print("blink_arc driver ok")

# --- ripsipivot: keyframet pois, driver tilalle
piv = bpy.data.objects["lash_pivot"]
piv.animation_data_clear()
fcd = piv.driver_add("rotation_euler", 0)
fcd.driver.type = 'SCRIPTED'
var = fcd.driver.variables.new()
var.name = "bc"
var.targets[0].id_type = 'KEY'
var.targets[0].id = sk
var.targets[0].data_path = 'key_blocks["blink_close"].value'
fcd.driver.expression = f"-{0.9*THETA:.4f}*bc"
print("ripsidriver ok")

# --- Bellin ilmiö: silmämuna ylös kiinni-tilassa (delta-rotaatio)
eyeball = bpy.data.objects["Eyeball"]
try:
    eyeball.driver_remove("delta_rotation_euler", 0)
except Exception:
    pass
fcd = eyeball.driver_add("delta_rotation_euler", 0)
fcd.driver.type = 'SCRIPTED'
var = fcd.driver.variables.new()
var.name = "bc"
var.targets[0].id_type = 'KEY'
var.targets[0].id = sk
var.targets[0].data_path = 'key_blocks["blink_close"].value'
fcd.driver.expression = f"-{math.radians(12):.4f}*bc"
print("Bell-driver ok (suunta tarkistetaan renderistä)")

# --- uusi avautumiskäyrä: raskas raotus -> flutter -> auki
bag = sk.animation_data.action.layers[0].strips[0].channelbag(sk.animation_data.action_slot)
for fc in list(bag.fcurves):
    if "blink_close" in fc.data_path:
        bag.fcurves.remove(fc)
kb.value = 0.0
KEYS = [(1, 1.0, 'EASE_OUT'), (11, 0.5, 'EASE_IN_OUT'), (13, 0.3, 'EASE_IN_OUT'),
        (15, 1.0, 'EASE_IN'), (16, 1.0, 'EASE_OUT'), (22, 0.12, 'EASE_IN_OUT'),
        (28, 0.0, 'EASE_OUT')]
for fr, val, ease in KEYS:
    kb.value = val
    kb.keyframe_insert("value", frame=fr)
kb.value = 0.0
for fc in bag.fcurves:
    if "blink_close" in fc.data_path:
        for kp, (fr, val, ease) in zip(sorted(fc.keyframe_points, key=lambda k: k.co.x), KEYS):
            kp.interpolation = 'BEZIER'
            kp.easing = ease
        fc.update()
print("avautumiskäyrä: 1.0 -> raotus -> flutter fr15 -> auki fr28")
bpy.ops.wm.save_mainfile()

prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = 'METAL'
prefs.refresh_devices()
for dv in prefs.devices:
    dv.use = True
scene.cycles.device = 'GPU'
scene.cycles.samples = 32
scene.render.resolution_percentage = 50
for fr in (1, 13, 15, 24):
    scene.frame_set(fr)
    scene.render.filepath = f"/Users/mikkonurminen/Desktop/3D BLENDER/the-weekend/proof_blink6_{fr:03d}.png"
    bpy.ops.render.render(write_still=True)
    print(f"still fr{fr} ok")
