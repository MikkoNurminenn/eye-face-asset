import bpy, math
from mathutils import Vector, Matrix
from collections import defaultdict

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
arc = sk.key_blocks["blink_arc"]
basis = sk.key_blocks["Basis"]
mw = head.matrix_world
inv = mw.inverted()

def W(i):  # basis-verteksi worldissa suhteessa silmän keskustaan
    return (mw @ basis.data[i].co) - C
def phi_of(p): return math.atan2(p.dot(up), p.dot(front))

# ---------- 1) reunarengas ja sen järjestys
cnt = defaultdict(list)
for poly in me.polygons:
    n = len(poly.vertices)
    for k in range(n):
        a, b = poly.vertices[k], poly.vertices[(k + 1) % n]
        cnt[(min(a, b), max(a, b))].append(poly.index)
rim_edges = [(a, b) for (a, b), fs in cnt.items() if len(fs) == 1
             and W(a).length < 2.5 * R]
adj = defaultdict(list)
for a, b in rim_edges:
    adj[a].append(b); adj[b].append(a)
start = rim_edges[0][0]
loop = [start]
prev = None
cur = start
while True:
    nxts = [v for v in adj[cur] if v != prev]
    if not nxts:
        break
    prev, cur = cur, nxts[0]
    if cur == start:
        break
    loop.append(cur)
print(f"rengas: {len(loop)} verteksiä (reunoja {len(rim_edges)})")

# kanthukset = renkaan ääripäät sivusuunnassa
svals = [W(i).dot(side) for i in loop]
i_min = svals.index(min(svals)); i_max = svals.index(max(svals))
a, b = sorted((i_min, i_max))
arc1 = loop[a:b + 1]
arc2 = loop[b:] + loop[:a + 1]
phi1 = sum(phi_of(W(i)) for i in arc1) / len(arc1)
phi2 = sum(phi_of(W(i)) for i in arc2) / len(arc2)
upper_chain = arc1 if phi1 > phi2 else arc2
lower_chain = arc2 if phi1 > phi2 else arc1
S0, S1 = min(svals), max(svals)
print(f"yläketju {len(upper_chain)} v (phi~{math.degrees(max(phi1,phi2)):.0f}°), "
      f"alaketju {len(lower_chain)} v (phi~{math.degrees(min(phi1,phi2)):.0f}°), "
      f"s-alue {S0*1000:.1f}..{S1*1000:.1f} mm")

# ---------- 2) ketjut funktioina s:stä (lineaari-interp + kevyt siloitus)
def chain_fn(chain):
    pts = sorted(((W(i).dot(side), phi_of(W(i))) for i in chain))
    ss = [p[0] for p in pts]
    ps = [p[1] for p in pts]
    ps_s = [ps[max(0, j-1):(j+2)] and sum(ps[max(0, j-1):j+2]) / len(ps[max(0, j-1):j+2])
            for j in range(len(ps))]
    def f(s):
        if s <= ss[0]: return ps_s[0]
        if s >= ss[-1]: return ps_s[-1]
        for j in range(len(ss) - 1):
            if ss[j] <= s <= ss[j + 1]:
                t = (s - ss[j]) / max(1e-9, ss[j + 1] - ss[j])
                return ps_s[j] * (1 - t) + ps_s[j + 1] * t
        return ps_s[-1]
    return f
phi_u = chain_fn(upper_chain)
phi_l = chain_fn(lower_chain)

def chain3_fn(chain):
    pts = sorted(((W(i).dot(side), W(i)) for i in chain), key=lambda x: x[0])
    ss = [p[0] for p in pts]
    vs = [p[1] for p in pts]
    vs_s = [sum(vs[max(0, j-1):j+2], Vector()) / len(vs[max(0, j-1):j+2])
            for j in range(len(vs))]
    def f(sv):
        if sv <= ss[0]: return vs_s[0]
        if sv >= ss[-1]: return vs_s[-1]
        for j in range(len(ss) - 1):
            if ss[j] <= sv <= ss[j + 1]:
                t = (sv - ss[j]) / max(1e-9, ss[j + 1] - ss[j])
                return vs_s[j] * (1 - t) + vs_s[j + 1] * t
        return vs_s[-1]
    return f
L3 = chain3_fn(lower_chain)
mid = (S0 + S1) / 2
print(f"keskellä: ylä {math.degrees(phi_u(mid)):.0f}°, ala {math.degrees(phi_l(mid)):.0f}°")

FOLD = math.radians(55)
OVER = math.radians(2.5)
LOWSPAN = math.radians(25)

def meeting(s):
    return phi_l(s) + 0.12 * (phi_u(s) - phi_l(s))

# ---------- 3) verteksien siirto marginvastaavuudella
n_moved = 0
for i, v in enumerate(me.vertices):
    p = W(i)
    r = p.length
    f = p.dot(front)
    s = p.dot(side)
    lat = 0.0
    if s < S0: lat = S0 - s
    if s > S1: lat = s - S1
    if r > 2.1 * R or f < -0.1 * R or lat > 0.4 * R:
        kb.data[i].co = basis.data[i].co
        arc.data[i].co = basis.data[i].co
        continue
    w_lat = max(0.0, 1.0 - lat / (0.4 * R))
    w_r = max(0.0, 1.0 - max(0.0, r - R) / (0.9 * R))
    w_r = w_r * w_r * (3 - 2 * w_r)
    phi = phi_of(p)
    pu, pl, M = phi_u(s), phi_l(s), meeting(s)
    gap = pu - pl
    if gap < math.radians(2):
        kb.data[i].co = basis.data[i].co
        arc.data[i].co = basis.data[i].co
        continue
    if phi >= (pu + pl) / 2:
        fold_line = pu + FOLD
        t = (fold_line - phi) / max(1e-6, fold_line - pu)
        t = max(0.0, min(1.15, t))
        delta = pu - (M - OVER)
        ang = -t * delta * w_lat * max(w_r, 0.55 if t > 0.95 else 0.0)
    else:
        tl = 1.0 - (pl - phi) / LOWSPAN
        tl = max(0.0, min(1.0, tl))
        delta = M - pl
        ang = (tl ** 1.2) * delta * w_lat * max(w_r, 0.55 if tl > 0.95 else 0.0)
    if abs(ang) < 1e-6:
        kb.data[i].co = basis.data[i].co
        arc.data[i].co = basis.data[i].co
        continue
    p_closed = Matrix.Rotation(ang, 4, side) @ p
    du = p_closed.dot(up) - p.dot(up)
    want_down = phi >= (pu + pl) / 2
    if (want_down and du > 0) or ((not want_down) and du < 0):
        p_closed = Matrix.Rotation(-ang, 4, side) @ p
    if want_down:
        # marginrenkaan snap alareunan 3D-kayralle (+iho paalle)
        snap_t = max(0.0, min(1.0, (t - 0.82) / 0.18)) if 't' in dir() else 0.0
        snap_t = snap_t * snap_t * (3 - 2 * snap_t)
        if snap_t > 0:
            anchor = L3(s).copy()
            anchor = anchor.normalized() * (anchor.length + 0.0008)
            anchor = Matrix.Rotation(math.radians(2.0), 4, side) @ anchor
            p_closed = p_closed * (1 - snap_t) + anchor * snap_t
    kb.data[i].co = inv @ (C + p_closed)
    p_half = Matrix.Rotation(ang * 0.5, 4, side) @ p
    chord_mid = (p + p_closed) * 0.5
    arc.data[i].co = inv @ (C + (p + (p_half - chord_mid)))
    n_moved += 1
print(f"siirrettyjä: {n_moved}")

# ---------- 4) ripsidriver keskimarginin todelliseen pyyhkäisyyn
delta_c = phi_u(mid) - (meeting(mid) - OVER)
print(f"marginpyyhkäisy keskellä: {math.degrees(delta_c):.0f}°")
piv = bpy.data.objects["lash_pivot"]
for fc in list(piv.animation_data.drivers if piv.animation_data else []):
    piv.animation_data.drivers.remove(fc)
fcd = piv.driver_add("rotation_euler", 0)
fcd.driver.type = 'SCRIPTED'
var = fcd.driver.variables.new()
var.name = "bc"
var.targets[0].id_type = 'KEY'
var.targets[0].id = sk
var.targets[0].data_path = 'key_blocks["blink_close"].value'
fcd.driver.expression = f"-{0.95*delta_c:.4f}*bc"

# alaripsille oma pivot
lpiv = bpy.data.objects.get("lash_pivot_lower")
if not lpiv:
    lpiv = bpy.data.objects.new("lash_pivot_lower", None)
    scene.collection.objects.link(lpiv)
lpiv.matrix_world = piv.matrix_world.copy()
lash_lo = bpy.data.objects["lashes_lower"]
if lash_lo.parent != lpiv:
    m = lash_lo.matrix_world.copy()
    lash_lo.parent = lpiv
    lash_lo.matrix_world = m
delta_low = meeting(mid) - phi_l(mid)
fcd = lpiv.driver_add("rotation_euler", 0)
fcd.driver.type = 'SCRIPTED'
var = fcd.driver.variables.new()
var.name = "bc"
var.targets[0].id_type = 'KEY'
var.targets[0].id = sk
var.targets[0].data_path = 'key_blocks["blink_close"].value'
fcd.driver.expression = f"{0.9*delta_low:.4f}*bc"
print(f"ripsidriverit: ylä -{math.degrees(0.95*delta_c):.0f}°, ala +{math.degrees(0.9*delta_low):.0f}°")

# upotus kevyemmäksi (0.8 mm)
eyeb = bpy.data.objects["Eyeball"]
for fc in eyeb.animation_data.drivers:
    if fc.data_path == "delta_location":
        num = float(fc.driver.expression.split("*")[0])
        fc.driver.expression = f"{num*0.53:.6f}*bc"
print("upotus 0.8 mm")
bpy.ops.wm.save_mainfile()

# ---------- 5) diagnostiikka
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = 'METAL'
prefs.refresh_devices()
for dv in prefs.devices:
    dv.use = True
scene.cycles.device = 'GPU'
scene.cycles.samples = 32
scene.frame_set(1)
r = scene.render
r.resolution_percentage = 100
r.use_border = True
r.use_crop_to_border = True
r.border_min_x, r.border_max_x = 0.0, 0.75
r.border_min_y, r.border_max_y = 0.40, 0.62
r.filepath = "/Users/mikkonurminen/Desktop/3D BLENDER/the-weekend/diag_seam_v13.png"
bpy.ops.render.render(write_still=True)
scene.frame_set(13)
r.filepath = "/Users/mikkonurminen/Desktop/3D BLENDER/the-weekend/diag_open_v13.png"
bpy.ops.render.render(write_still=True)
r.use_border = False
r.use_crop_to_border = False
print("diagit ok")
