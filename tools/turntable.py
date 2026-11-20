# Drehteller fuer das GitHub-Profil: baut Samis Späti (scene2.py) einmal auf,
# stellt dann jedes Getraenk und jeden Pokal einzeln ins Studio und rendert N Bilder rundherum.
# Aufruf: Blender -b -P tools/turntable.py -- <outdir> <frames> <samples> <id,id,...|all>
import sys, os, math

BL = "/Users/samimagdouli/Desktop/APP/portfolien/spaeti/blender"
args = sys.argv[sys.argv.index("--") + 1:]
OUTDIR, NF, SPP = args[0], int(args[1]), int(args[2])
WANT = args[3].split(",") if len(args) > 3 else ["all"]

sys.argv = [sys.argv[0], "--", "none"]          # scene2/modes2: kein Render-Modus, nur aufbauen
G = {"__file__": os.path.join(BL, "scene2.py"), "__name__": "__main__"}
exec(compile(open(G["__file__"]).read(), G["__file__"], "exec"), G)

bpy, Vector = G["bpy"], G["Vector"]
scene, COL, lin, aim = G["scene"], G["COL"], G["lin"], G["aim"]
masters, instance, DRINKS = G["masters"], G["instance"], G["DRINKS"]
CAN_SCALE = G.get("CAN_SCALE", {})
trophies = G.get("trophies", {})
print("TROPHIES", list(trophies))

ids = [p for p in DRINKS if p != "nta"] + list(trophies)
if WANT != ["all"]:
    ids = [p for p in ids if p in WANT]

for o in bpy.data.objects:
    if o.type in ("MESH", "CURVE", "FONT", "LIGHT"):
        o.hide_render = True

# Lichtbox: Studio-HDRI nur fuer Spiegelung und Glas, fuer die Kamera transparent
world = G["world"]; wn = world.node_tree; bg = G["bg"]
wn.links.clear()
env = wn.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load("/Applications/Blender.app/Contents/Resources/5.2/datafiles/studiolights/world/studio.exr")
wn.links.new(env.outputs["Color"], bg.inputs["Color"]); bg.inputs["Strength"].default_value = float(os.environ.get("ENV_STRENGTH", "1.0"))
wout = next(n for n in wn.nodes if n.type == "OUTPUT_WORLD"); wn.links.new(bg.outputs[0], wout.inputs[0])
scene.render.film_transparent = True

C = Vector((0, -5, 0))
cd = bpy.data.cameras.new("tcam"); cd.lens = 85
tc = bpy.data.objects.new("tcam", cd); COL.objects.link(tc); scene.camera = tc
lights = []

def area(nm, loc, size, energy, col, tgt, sy=None):
    Ld = bpy.data.lights.new(nm, "AREA"); Ld.size = size; Ld.energy = energy; Ld.color = lin(col)
    if sy:
        Ld.shape = "RECTANGLE"; Ld.size_y = sy
    o = bpy.data.objects.new(nm, Ld); COL.objects.link(o); aim(o, Vector(loc), tgt)
    lights.append(o)

def extent_of(root):
    """Hoehe, Boden-z und groesster Abstand zur Drehachse (fuer den Bildausschnitt beim Drehen)."""
    zs, rs = [], []
    for o in [root] + list(root.children_recursive):
        if o.type == "MESH":
            for v in o.bound_box:
                p = o.matrix_world @ Vector(v)
                zs.append(p.z); rs.append(math.hypot(p.x - C.x, p.y - C.y))
    return max(zs) - min(zs), min(zs), max(rs)

G["cycles"](SPP, 360, 480)
scene.cycles.adaptive_threshold = 0.03

for pid in ids:
    if pid in trophies:
        g = trophies[pid]; g.parent = None; g.location = C; g.scale = (1, 1, 1); g.rotation_euler = (0, 0, 0)
    else:
        g = instance(masters[pid], "turn_" + pid, None, C, 0)
        if pid in CAN_SCALE:
            sx, sz = CAN_SCALE[pid]; g.scale = (sx, sx, sz)
    for o in [g] + list(g.children_recursive):
        o.hide_render = False
    bpy.context.view_layer.update()
    h, z0, rad = extent_of(g)
    mid = Vector((0, -5, z0 + h / 2))
    frame_h = max(h, 2 * rad * 480 / 360 * 0.95)
    for o in lights:
        bpy.data.objects.remove(o, do_unlink=True)
    lights.clear()
    area("key", (-0.6 * h / 0.27, -5 - 0.8 * h / 0.27, z0 + h / 2 + 0.5 * h / 0.27), 0.6 * h / 0.27, 30 * (h / 0.27) ** 2, "#fff4e6", mid)
    area("rimL", (-0.5 * h / 0.27, -5 + 0.4 * h / 0.27, z0 + h / 2 + 0.1), 0.06, 12 * (h / 0.27) ** 2, "#dfeaff", mid, 0.6 * h / 0.27)
    area("rimR", (0.5 * h / 0.27, -5 + 0.4 * h / 0.27, z0 + h / 2 + 0.1), 0.06, 12 * (h / 0.27) ** 2, "#dfeaff", mid, 0.6 * h / 0.27)
    area("strip", (0.35 * h / 0.27, -5 - 0.7 * h / 0.27, z0 + h / 2), 0.05, 10 * (h / 0.27) ** 2, "#ffffff", mid, 0.5 * h / 0.27)
    # Leuchtwand hinter dem Teil (wie die Rueckwand im Kuehlschrank): Glas und Fluessigkeit bekommen ihre Farbe,
    # die Kamera sieht die Wand nicht (Film bleibt transparent). Staerke ~1 = Weiss, also kein Ausbrennen.
    if "backwall" not in bpy.data.objects:
        bpy.ops.mesh.primitive_plane_add(size=1.0)
        wall = bpy.context.active_object; wall.name = "backwall"
        m, nt = G["new_mat"]("backwall_mat")
        em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (1, 1, 1, 1)
        em.inputs["Strength"].default_value = float(os.environ.get("WALL", "1.2"))
        nt.links.new(em.outputs[0], G["out_node"](nt).inputs[0]); wall.data.materials.append(m)
        wall.visible_camera = False; wall.visible_shadow = False
    wall = bpy.data.objects["backwall"]; wall.hide_render = False
    wall.scale = (8 * frame_h, 8 * frame_h, 1)
    wall.location = (0, -5 + 3 * frame_h, z0 + h / 2); wall.rotation_euler = (math.pi / 2, 0, 0)
    dist = frame_h / (0.8 * 0.4228) * 1.12
    aim(tc, Vector((0, -5 - dist * math.cos(0.12), z0 + h / 2 + dist * math.sin(0.12))), mid)
    d = os.path.join(OUTDIR, pid); os.makedirs(d, exist_ok=True)
    for f in range(NF):
        g.rotation_euler = (0, 0, 2 * math.pi * f / NF)
        scene.render.filepath = os.path.join(d, "%03d.png" % f)
        scene.render.image_settings.color_mode = "RGBA"
        bpy.ops.render.render(write_still=True)
    for o in [g] + list(g.children_recursive):
        o.hide_render = True
    print("TURN_DONE", pid, flush=True)
print("ALL_DONE")
