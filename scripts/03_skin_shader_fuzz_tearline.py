import bpy, math, time
from mathutils import Vector
from collections import defaultdict
scene = bpy.context.scene
head = bpy.data.objects["MetaHumanHead_Textured"]
me = head.data
eye = bpy.data.objects["Eyeball"]
pts = [eye.matrix_world @ Vector(c) for c in eye.bound_box]
C = sum(pts, Vector()) / 8
R = max(Vector(map(max, *pts)) - Vector(map(min, *pts))) / 2
C_local = head.matrix_world.inverted() @ C
print(f"silmä C={tuple(round(v,3) for v in C)} R={R:.4f}")

# ---------- 1) ihon shader
m = bpy.data.materials["Material_MetaHumanHead"]
nt = m.node_tree
p = nt.nodes["Principled BSDF"]
def S(name, val):
    if name in [s.name for s in p.inputs]: p.inputs[name].default_value = val
S("Subsurface Weight", 0.85); S("Subsurface Radius", (1.0, 0.38, 0.19)); S("Subsurface Scale", 0.0037)
S("IOR", 1.40); S("Specular IOR Level", 0.55); S("Coat Weight", 0.12); S("Coat Roughness", 0.28)
# karheus: albedo-map * 0.62 + noise-vaihtelu
rough_src = p.inputs["Roughness"].links[0].from_socket
mulR = nt.nodes.new("ShaderNodeMath"); mulR.operation = 'MULTIPLY'; mulR.inputs[1].default_value = 0.62
nt.links.new(rough_src, mulR.inputs[0])
tc = nt.nodes.new("ShaderNodeTexCoord")
nvar = nt.nodes.new("ShaderNodeTexNoise"); nvar.inputs["Scale"].default_value = 900; nvar.inputs["Detail"].default_value = 3
nt.links.new(tc.outputs["Object"], nvar.inputs["Vector"])
rv = nt.nodes.new("ShaderNodeMapRange"); rv.inputs["From Min"].default_value = 0.3; rv.inputs["From Max"].default_value = 0.7
rv.inputs["To Min"].default_value = -0.07; rv.inputs["To Max"].default_value = 0.07
nt.links.new(nvar.outputs["Fac"], rv.inputs["Value"])
addR = nt.nodes.new("ShaderNodeMath"); addR.operation = 'ADD'
nt.links.new(mulR.outputs[0], addR.inputs[0]); nt.links.new(rv.outputs["Result"], addR.inputs[1])
addR.use_clamp = True
nt.links.new(addR.outputs[0], p.inputs["Roughness"])
# mikrodetalji: huokoset (voronoi) + hienot rypyt (noise) -> bump ketjun päähän
vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 2600
vor.inputs["Randomness"].default_value = 1.0
nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
pore = nt.nodes.new("ShaderNodeMapRange"); pore.inputs["From Min"].default_value = 0.0; pore.inputs["From Max"].default_value = 0.25
pore.inputs["To Min"].default_value = 0.0; pore.inputs["To Max"].default_value = 1.0
nt.links.new(vor.outputs["Distance"], pore.inputs["Value"])
fine = nt.nodes.new("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 4200; fine.inputs["Detail"].default_value = 6
fine.inputs["Roughness"].default_value = 0.7
nt.links.new(tc.outputs["Object"], fine.inputs["Vector"])
mixH = nt.nodes.new("ShaderNodeMath"); mixH.operation = 'MULTIPLY_ADD'
nt.links.new(pore.outputs["Result"], mixH.inputs[0]); mixH.inputs[1].default_value = 0.6
nt.links.new(fine.outputs["Fac"], mixH.inputs[2])
b2 = nt.nodes.new("ShaderNodeBump"); b2.inputs["Strength"].default_value = 0.35; b2.inputs["Distance"].default_value = 0.00012
prev_normal = p.inputs["Normal"].links[0].from_socket
nt.links.new(mixH.outputs[0], b2.inputs["Height"]); nt.links.new(prev_normal, b2.inputs["Normal"])
nt.links.new(b2.outputs["Normal"], p.inputs["Normal"])
# punerrus luomien reunoilla / sisänurkassa
base_src = p.inputs["Base Color"].links[0].from_socket
ctr = nt.nodes.new("ShaderNodeCombineXYZ"); ctr.inputs[0].default_value = C_local.x; ctr.inputs[1].default_value = C_local.y; ctr.inputs[2].default_value = C_local.z
sub = nt.nodes.new("ShaderNodeVectorMath"); sub.operation = 'DISTANCE'
nt.links.new(tc.outputs["Object"], sub.inputs[0]); nt.links.new(ctr.outputs[0], sub.inputs[1])
rm = nt.nodes.new("ShaderNodeMapRange"); rm.inputs["From Min"].default_value = R*1.05; rm.inputs["From Max"].default_value = R*2.6
rm.inputs["To Min"].default_value = 0.30; rm.inputs["To Max"].default_value = 0.0
nt.links.new(sub.outputs["Value"], rm.inputs["Value"])
red = nt.nodes.new("ShaderNodeMix"); red.data_type = 'RGBA'; red.blend_type = 'MULTIPLY'
red.inputs[7].default_value = (1.18, 0.78, 0.78, 1.0)
nt.links.new(base_src, red.inputs[6]); nt.links.new(rm.outputs["Result"], red.inputs["Factor"])
nt.links.new(red.outputs[2], p.inputs["Base Color"])
print("shader ok")

# ---------- 2) untuvakarvat silmän ympärille
vg = head.vertex_groups.get("fuzz_zone") or head.vertex_groups.new(name="fuzz_zone")
n_fz = 0
for v in me.vertices:
    d = (head.matrix_world @ v.co - C).length
    if d < 0.075:
        w = 1.0 if d > R*1.15 else 0.15
        vg.add([v.index], w, 'REPLACE'); n_fz += 1
for ps in list(head.particle_systems):
    if ps.name == "PeachFuzz":
        bpy.context.view_layer.objects.active = head
        head.modifiers.remove(head.modifiers[ps.name]) if ps.name in head.modifiers else None
mod = head.modifiers.new("PeachFuzz", 'PARTICLE_SYSTEM')
ps = head.particle_systems[-1]; ps.name = "PeachFuzz"
st = ps.settings; st.name = "PeachFuzzSettings"
st.type = 'HAIR'; st.count = 45000; st.hair_length = 0.0013; st.length_random = 0.6
st.use_advanced_hair = True; st.hair_step = 3
st.root_radius = 0.03; st.tip_radius = 0.0; st.radius_scale = 0.001
st.use_emit_random = True; st.emit_from = 'FACE'; st.use_even_distribution = True
ps.vertex_group_density = "fuzz_zone"; ps.vertex_group_length = "fuzz_zone"
st.factor_random = 0.002; st.brownian_factor = 0.0005   # kevyt sekasuunta
fuzz = bpy.data.materials.get("PeachFuzz") or bpy.data.materials.new("PeachFuzz")
fuzz.use_nodes = True; fnt = fuzz.node_tree; fnt.nodes.clear()
fo = fnt.nodes.new("ShaderNodeOutputMaterial"); fh = fnt.nodes.new("ShaderNodeBsdfHairPrincipled")
try:
    fh.parametrization = "MELANIN"
    fh.inputs["Melanin"].default_value = 0.12
except Exception:
    fh.inputs["Color"].default_value = (0.55, 0.42, 0.33, 1.0)
fh.inputs["Roughness"].default_value = 0.45
fnt.links.new(fh.outputs["BSDF"], fo.inputs["Surface"])
if fuzz.name not in [mm.name for mm in me.materials]: me.materials.append(fuzz)
st.material_slot = fuzz.name
print(f"untuvakarvat: {n_fz} v vyöhyke, {st.count} karvaa")

# ---------- 3) kyynelmeniski alaluomen reunaan
cnt = defaultdict(int)
for poly in me.polygons:
    n = len(poly.vertices)
    for k in range(n):
        a, b = poly.vertices[k], poly.vertices[(k+1) % n]; cnt[(min(a,b), max(a,b))] += 1
basis = me.shape_keys.key_blocks["Basis"]
def W(i): return (head.matrix_world @ basis.data[i].co)
rim = [(a,b) for (a,b),c in cnt.items() if c == 1 and (W(a)-C).length < 2.5*R]
adj = defaultdict(list)
for a,b in rim: adj[a].append(b); adj[b].append(a)
start = rim[0][0]; loop = [start]; prev=None; cur=start
while True:
    nx = [v for v in adj[cur] if v != prev]
    if not nx: break
    prev, cur = cur, nx[0]
    if cur == start: break
    loop.append(cur)
cam = bpy.data.objects["hero_socket"]; scene.frame_set(30)
front = (cam.matrix_world.translation - C).normalized()
side = front.cross(Vector((0,0,1))).normalized()*-1; up = side.cross(front)*-1
if up.z < 0: up=-up; side=-side
lower = [i for i in loop if (W(i)-C).dot(up) < -0.05*R]
lower.sort(key=lambda i: (W(i)-C).dot(side))
verts, faces = [], []
rad = 0.00035
for k, i in enumerate(lower):
    pw = W(i) + (C - W(i)).normalized()*0.0004 - up*0.0002
    t = (W(lower[min(k+1,len(lower)-1)]) - W(lower[max(k-1,0)])).normalized()
    n1 = t.cross(front).normalized(); n2 = t.cross(n1).normalized()
    base = len(verts)
    for j in range(8):
        a = 2*math.pi*j/8
        verts.append(pw + n1*math.cos(a)*rad + n2*math.sin(a)*rad)
    if k > 0:
        for j in range(8):
            faces.append((base-8+j, base-8+(j+1)%8, base+(j+1)%8, base+j))
tm = bpy.data.meshes.new("TearLine"); tm.from_pydata([head.matrix_world.inverted() @ v for v in verts], [], faces); tm.update()
old = bpy.data.objects.get("TearLine")
if old: bpy.data.objects.remove(old, do_unlink=True)
tear = bpy.data.objects.new("TearLine", tm); scene.collection.objects.link(tear)
tear.parent = head; tear.matrix_parent_inverse = head.matrix_world.inverted()
for pg in tm.polygons: pg.use_smooth = True
tmat = bpy.data.materials.get("TearFilm") or bpy.data.materials.new("TearFilm")
tmat.use_nodes = True; tb = tmat.node_tree.nodes["Principled BSDF"]
tb.inputs["Base Color"].default_value = (1,1,1,1); tb.inputs["Roughness"].default_value = 0.03
tb.inputs["IOR"].default_value = 1.336
for nm in ("Transmission Weight",):
    if nm in [s.name for s in tb.inputs]: tb.inputs[nm].default_value = 1.0
tm.materials.append(tmat)
print(f"kyynelviiva: {len(lower)} pistettä")

# ---------- 4) takavalo untuvakarvoille
ld = bpy.data.lights.new("FuzzRim", 'AREA'); ld.energy = 3.0; ld.size = 0.15; ld.color = (1.0, 0.92, 0.85)
lo = bpy.data.objects.new("FuzzRim", ld); scene.collection.objects.link(lo)
lo.location = C - front*0.18 + side*0.22 + up*0.10
d = (C - lo.location).normalized(); lo.rotation_euler = d.to_track_quat('-Z','Y').to_euler()

bpy.ops.wm.save_as_mainfile(filepath="/Users/mikkonurminen/Desktop/3D BLENDER/the-weekend/eye-working-v004.blend")
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = 'METAL'; prefs.refresh_devices()
for dv in prefs.devices: dv.use = True
scene.cycles.device = 'GPU'; scene.cycles.samples = 64
scene.render.resolution_percentage = 50
scene.frame_set(40)
scene.render.filepath = "/Users/mikkonurminen/Desktop/3D BLENDER/the-weekend/proof_skin_v2.png"
t0 = time.time(); bpy.ops.render.render(write_still=True); print(f"still ok {time.time()-t0:.0f} s")
