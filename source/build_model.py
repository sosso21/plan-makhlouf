import numpy as np, trimesh
from trimesh.visual.material import PBRMaterial
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from shapely.geometry import Polygon, box as sbox
from collections import defaultdict

H = 2.9           # hauteur sous plafond
SLAB = 0.15
FL1 = H + SLAB    # niveau fini de l'étage
DOOR = 2.15
groups = defaultdict(list)
PREFIX, YOFF = '', 0.0

C = dict(
    wall=(0.96,0.93,0.86,1), stone=(0.72,0.62,0.50,1), column=(0.62,0.62,0.64,1),
    slab=(0.55,0.55,0.55,1), grass=(0.45,0.66,0.35,1), paving=(0.70,0.67,0.62,1),
    garage=(0.66,0.68,0.70,1), wet=(0.62,0.80,0.90,1), bed_floor=(0.78,0.58,0.38,1),
    living=(0.90,0.80,0.62,1), kitchen=(0.93,0.70,0.55,1), hall=(0.88,0.86,0.80,1),
    terrace=(0.80,0.45,0.30,1), wood=(0.55,0.35,0.20,1), white=(0.97,0.97,0.97,1),
    glass=(0.55,0.80,0.95,0.45), door=(0.60,0.40,0.22,1), garagedoor=(0.35,0.40,0.48,1),
    sofa=(0.20,0.35,0.65,1), car=(0.80,0.12,0.12,1), black=(0.08,0.08,0.08,1),
    counter=(0.25,0.25,0.28,1), fire=(0.95,0.45,0.10,1), label=(0.15,0.15,0.20,1),
    pillow=(0.85,0.75,0.55,1), plant=(0.20,0.55,0.25,1), tile=(0.70,0.28,0.18,1),
    bed2=(0.55,0.65,0.45,1), bed3=(0.75,0.45,0.55,1),
)

def add(m, color, group):
    groups[PREFIX + group].append((m, color))

def box(xa, xb, za, zb, ya, yb, color, group):
    m = trimesh.creation.box(extents=[xb-xa, yb-ya, zb-za])
    m.apply_translation([(xa+xb)/2, (ya+yb)/2 + YOFF, (za+zb)/2])
    add(m, color, group)

def cyl(x, z, r, ya, yb, color, group):
    m = trimesh.creation.cylinder(radius=r, height=yb-ya, sections=24)
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1,0,0]))
    m.apply_translation([x, (ya+yb)/2 + YOFF, z])
    add(m, color, group)

def prism(poly, ya, yb, color, group):
    """Polygone shapely dans le plan (X, Z) extrudé verticalement de ya à yb."""
    m = trimesh.creation.extrude_polygon(poly, yb-ya)
    M = np.array([[1,0,0,0],[0,0,1,0],[0,1,0,0],[0,0,0,1]], float)
    m.apply_transform(M); m.invert()
    m.apply_translation([0, ya + YOFF, 0])
    add(m, color, group)

def slope(xa, xb, za, zb, y_hi, y_lo, toward, color, group, t=0.08):
    """Pan de toiture : haut côté opposé à `toward` ('-x', '+x')."""
    pts = []
    for x in (xa, xb):
        for z in (za, zb):
            low = (x == xa) if toward == '-x' else (x == xb)
            y = y_lo if low else y_hi
            pts += [[x, y + YOFF, z], [x, y + t + YOFF, z]]
    add(trimesh.convex.convex_hull(np.array(pts)), color, group)

def wall(xa, xb, za, zb, openings=(), color='wall', h=H):
    along_x = (xb-xa) >= (zb-za)
    a0, a1 = (xa, xb) if along_x else (za, zb)
    def piece(s, e, ya, yb, col, grp):
        if e-s < 1e-3 or yb-ya < 1e-3: return
        if along_x: box(s, e, za, zb, ya, yb, C[col], grp)
        else:       box(xa, xb, s, e, ya, yb, C[col], grp)
    cur = a0
    for (s, e, lo, hi, kind) in sorted(openings):
        piece(cur, s, 0, h, color, 'Murs')
        piece(s, e, 0, lo, color, 'Murs')
        piece(s, e, hi, h, color, 'Murs')
        if kind:
            col = {'door':'door','win':'glass','gdoor':'garagedoor'}[kind]
            grp = 'Vitrages' if kind == 'win' else 'Portes'
            if along_x: m0, m1 = (za+zb)/2-0.02, (za+zb)/2+0.02; box(s, e, m0, m1, lo, hi, C[col], grp)
            else:       m0, m1 = (xa+xb)/2-0.02, (xa+xb)/2+0.02; box(m0, m1, s, e, lo, hi, C[col], grp)
        cur = e
    piece(cur, a1, 0, h, color, 'Murs')

def floor(xa, xb, za, zb, col, name, y=0.0):
    box(xa, xb, za, zb, y-0.01, y, C[col], 'Sol ' + name)

fp = FontProperties(family='DejaVu Sans', weight='bold')
def label(text, cx, cz, size=0.38, y=0.012):
    tp = TextPath((0, 0), text, size=size, prop=fp)
    geom = None
    for ring in tp.to_polygons():
        if len(ring) < 3: continue
        p = Polygon(ring).buffer(0)
        geom = p if geom is None else geom.symmetric_difference(p)
    polys = list(geom.geoms) if hasattr(geom, 'geoms') else [geom]
    minx, miny, maxx, maxy = geom.bounds
    for p in polys:
        m = trimesh.creation.extrude_polygon(p, 0.005)
        m.apply_translation([-(minx+maxx)/2, -(miny+maxy)/2, 0])
        m.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2, [1,0,0]))
        m.apply_translation([cx, y + YOFF, cz])
        add(m, C['label'], 'Etiquettes')

def bed(xa, xb, za, zb, sheet):
    """Lit, tête côté za."""
    box(xa, xb, za, zb, 0.0, 0.45, C['wood'], 'Lit')
    box(xa+0.05, xb-0.05, za+0.05, zb-0.05, 0.45, 0.62, C['white'], 'Lit')
    box(xa, xb, za, za+0.1, 0.0, 1.10, C['wood'], 'Lit')
    w = (xb-xa-0.3)/2
    box(xa+0.1, xa+0.1+w, za+0.15, za+0.55, 0.62, 0.75, C['pillow'], 'Lit')
    box(xb-0.1-w, xb-0.1, za+0.15, za+0.55, 0.62, 0.75, C['pillow'], 'Lit')
    box(xa+0.05, xb-0.05, za+(zb-za)*0.45, zb-0.05, 0.62, 0.66, C[sheet], 'Lit')

def sofa_L(x_in, x_out, z_top, z_bot, x_left):
    """Canapé d'angle : branche verticale x_in..x_out, branche basse x_left..x_in."""
    box(x_in, x_out, z_top, z_bot, 0, 0.42, C['sofa'], 'Salon')
    box(x_left, x_in, z_bot-0.9, z_bot, 0, 0.42, C['sofa'], 'Salon')
    box(x_out-0.3, x_out, z_top, z_bot, 0.42, 0.85, C['sofa'], 'Salon')
    box(x_left, x_out-0.3, z_bot-0.3, z_bot, 0.42, 0.85, C['sofa'], 'Salon')

# =====================================================================
#                           REZ-DE-CHAUSSÉE
# =====================================================================
PREFIX, YOFF = '', 0.0
T = 0.25
wall(0, 5.45, 0, T, color='stone')
wall(0, T, 0, 4.45, [(0.45, 3.55, 0, 2.5, 'gdoor')], color='stone')
wall(0, 2.72, 3.80, 4.45, color='stone')
wall(2.72, 4.95, 3.80, 3.95)
box(2.72, 4.80, 3.95, 4.42, 0, 2.3, C['wood'], 'Mobilier')
wall(5.35, 5.50, T, 2.75)
wall(4.80, 4.95, 2.88, 4.45, [(2.98, 3.80, 0, DOOR, 'door')])
wall(4.80, 6.32, 2.75, 2.88, [(5.58, 6.15, 0, DOOR, 'door')])
wall(5.35, 8.20, 0, T, [(5.60, 6.00, 1.6, 2.2, 'win'), (6.45, 7.05, 1.6, 2.2, 'win')], color='stone')
wall(6.18, 6.32, T, 2.75)
wall(8.08, 8.20, T, 2.88)
wall(6.32, 8.08, 2.75, 2.88, [(6.42, 7.15, 0, DOOR, 'door')])
wall(7.26, 7.38, 2.88, 4.30, [(3.30, 4.15, 0, DOOR, 'door')])
wall(4.95, 7.38, 4.30, 4.45, [(5.10, 6.20, 0, DOOR, None)])
wall(8.20, 12.25, 0, T, [(10.95, 11.75, 1.0, 2.2, 'win')], color='stone')
wall(12.0, 12.25, 0, 4.45, [(1.55, 2.90, 0.9, 2.2, 'win')], color='stone')
wall(7.38, 10.70, 4.30, 4.45)
wall(10.70, 12.25, 4.20, 4.45, color='stone')
wall(1.50, 1.75, 4.45, 9.35, [(4.65, 5.75, 0, 2.2, 'door'), (6.75, 7.85, 1.0, 2.2, 'win')], color='stone')
wall(1.75, 5.57, 5.93, 6.05, [(3.60, 4.60, 0, DOOR, 'door')])
wall(5.45, 5.57, 6.05, 9.35)
wall(1.75, 5.57, 9.20, 9.35, [(4.15, 5.35, 0, 2.2, 'win')], color='stone')
box(5.57, 6.32, 8.20, 9.35, 0, H, C['wall'], 'Murs')
wall(6.20, 6.35, 8.20, 11.95, [(9.75, 11.20, 0, 2.2, 'win')], color='stone')
wall(6.35, 10.95, 11.70, 11.95, [(7.90, 9.20, 0, 2.2, 'win')], color='stone')
wall(10.70, 10.95, 4.45, 11.70, color='stone')
box(5.57, 6.32, 6.90, 8.20, 0, H, C['stone'], 'Cheminee')
box(6.20, 6.33, 7.25, 7.85, 0.15, 0.95, C['black'], 'Cheminee')
box(6.10, 6.33, 7.35, 7.75, 0.15, 0.40, C['fire'], 'Cheminee')

for x in (1.6, 6.19, 10.8):
    for z in (0.15, 4.3, 8.3, 11.8):
        box(x-0.17, x+0.17, z-0.17, z+0.17, 0, H, C['column'], 'Poteaux')
box(12.25-0.34, 12.25, 0, 0.34, 0, H, C['column'], 'Poteaux')
box(12.25-0.34, 12.25, 4.11, 4.45, 0, H, C['column'], 'Poteaux')
# pergola terrasse
box(1.45, 6.35, 11.65, 11.95, H-0.25, H, C['column'], 'Pergola')
box(1.45, 1.75, 9.35, 11.95, H-0.25, H, C['column'], 'Pergola')
for z in (9.68, 10.08, 10.48, 10.90, 11.32):
    box(1.75, 6.20, z-0.04, z+0.04, H-0.15, H, C['wood'], 'Pergola')

box(-6, 18, -6, 18, -0.22, -0.15, C['grass'], 'Terrain')
box(0, 12.25, 0, 4.45, -0.15, -0.01, C['slab'], 'Dalle')
box(1.5, 10.95, 4.45, 9.35, -0.15, -0.01, C['slab'], 'Dalle')
box(6.2, 10.95, 9.35, 11.95, -0.15, -0.01, C['slab'], 'Dalle')
floor(0.25, 4.80, 0.25, 3.80, 'garage', 'Garage')
floor(4.80, 5.35, 0.25, 2.75, 'garage', 'Garage')
floor(5.50, 6.18, 0.25, 2.75, 'wet', 'WC')
floor(6.32, 8.08, 0.25, 2.75, 'wet', 'SDB')
floor(4.95, 7.26, 2.88, 4.30, 'hall', 'Hall')
floor(8.20, 12.0, 0.25, 4.30, 'bed_floor', 'Chambre')
floor(7.38, 8.20, 2.88, 4.30, 'bed_floor', 'Chambre')
floor(1.75, 6.32, 4.45, 5.93, 'hall', 'Hall entree')
floor(1.75, 5.45, 6.05, 9.20, 'kitchen', 'Cuisine')
floor(6.32, 10.70, 4.45, 11.70, 'living', 'Sejour')
floor(5.57, 6.32, 6.05, 6.90, 'living', 'Sejour')
floor(1.75, 6.20, 9.35, 11.95, 'terrace', 'Terrasse', y=-0.06)
floor(0, 1.50, 4.45, 11.95, 'paving', 'Dallage ext', y=-0.08)
floor(1.50, 1.75, 9.35, 11.95, 'paving', 'Dallage ext', y=-0.08)

# ---------- Escalier : départ dans le hall (ouest), quart tournant à l'est, arrivée vers le sud ----------
N_STRAIGHT, N_WIND = 12, 5
RISE = FL1 / (N_STRAIGHT + N_WIND + 1)
SX0, SX1, SZ0, SZ1 = 6.45, 9.65, 4.45, 5.45
run = (SX1 - SX0) / N_STRAIGHT
for i in range(N_STRAIGHT):
    box(SX0 + i*run, SX0 + (i+1)*run, SZ0, SZ1, 0, (i+1)*RISE, C['wood'], 'Escalier')
    xx = SX0 + (i+0.5)*run
    box(xx-0.015, xx+0.015, SZ1-0.04, SZ1-0.01, (i+1)*RISE, (i+1)*RISE+0.9, C['black'], 'Escalier')
    box(SX0+i*run, SX0+(i+1)*run, SZ1-0.05, SZ1, (i+1)*RISE+0.87, (i+1)*RISE+0.92, C['wood'], 'Escalier')
# marches balancées (quart tournant) autour du point (SX1, SZ1)
R = sbox(SX1, SZ0, 10.70, 5.90)
for k in range(N_WIND):
    a0 = -np.pi/2 + k*np.pi/N_WIND
    a1 = -np.pi/2 + (k+1)*np.pi/N_WIND
    sector = Polygon([(SX1, SZ1), (SX1 + 9*np.cos(a0), SZ1 + 9*np.sin(a0)),
                      (SX1 + 9*np.cos((a0+a1)/2), SZ1 + 9*np.sin((a0+a1)/2)),
                      (SX1 + 9*np.cos(a1), SZ1 + 9*np.sin(a1))])
    wedge = R.intersection(sector)
    if wedge.area > 1e-4:
        prism(wedge, 0, (N_STRAIGHT + k + 1)*RISE, C['wood'], 'Escalier')

# ---------- Mobilier RDC ----------
box(0.6, 4.6, 1.15, 2.95, 0.30, 1.05, C['car'], 'Voiture')
box(1.6, 3.7, 1.25, 2.85, 1.05, 1.50, C['glass'], 'Voiture')
for x in (1.3, 3.9):
    for z in (1.15, 2.95):
        m = trimesh.creation.cylinder(radius=0.33, height=0.22, sections=24)
        m.apply_translation([x, 0.33, z]); add(m, C['black'], 'Voiture')
bed(9.05, 10.95, 0.25, 2.45, 'sofa')
box(8.45, 8.95, 0.25, 0.70, 0, 0.55, C['wood'], 'Lit')
box(11.05, 11.55, 0.25, 0.70, 0, 0.55, C['wood'], 'Lit')
box(11.40, 12.0, 2.95, 4.25, 0, 2.2, C['wood'], 'Armoire')
box(5.65, 6.05, 0.30, 0.95, 0, 0.42, C['white'], 'Sanitaires')
box(5.65, 6.05, 0.25, 0.42, 0.42, 0.85, C['white'], 'Sanitaires')
box(6.35, 7.25, 0.28, 1.20, 0, 0.08, C['white'], 'Sanitaires')
box(6.35, 7.25, 1.18, 1.21, 0.08, 2.0, C['glass'], 'Sanitaires')
box(7.55, 8.05, 1.40, 2.10, 0, 0.85, C['white'], 'Sanitaires')
box(1.75, 2.35, 6.65, 9.20, 0, 0.86, C['white'], 'Cuisine')
box(2.35, 4.10, 8.60, 9.20, 0, 0.86, C['white'], 'Cuisine')
box(1.75, 2.38, 6.65, 9.20, 0.86, 0.90, C['counter'], 'Cuisine')
box(2.35, 4.10, 8.57, 9.20, 0.86, 0.90, C['counter'], 'Cuisine')
box(1.75, 2.10, 6.65, 8.40, 1.50, 2.20, C['wood'], 'Cuisine')
box(1.75, 2.40, 6.05, 6.62, 0, 1.95, C['white'], 'Cuisine')
box(3.0, 4.2, 6.9, 7.7, 0, 0.9, C['wood'], 'Cuisine')
box(3.0, 4.2, 6.9, 7.7, 0.9, 0.94, C['counter'], 'Cuisine')
box(7.25, 8.45, 6.25, 7.75, 0.72, 0.77, C['wood'], 'Salle a manger')
for x, z in [(7.35,6.35),(8.35,6.35),(7.35,7.65),(8.35,7.65)]:
    box(x-0.04, x+0.04, z-0.04, z+0.04, 0, 0.72, C['wood'], 'Salle a manger')
for x, z in [(7.05,6.6),(7.05,7.4),(8.65,6.6),(8.65,7.4),(7.85,6.0),(7.85,8.0)]:
    box(x-0.22, x+0.22, z-0.22, z+0.22, 0, 0.46, C['pillow'], 'Salle a manger')
sofa_L(9.45, 10.40, 8.10, 10.75, 8.00)
box(8.15, 8.90, 8.50, 9.55, 0, 0.40, C['wood'], 'Salon')
box(6.5, 7.0, 11.2, 11.65, 0, 0.35, C['wood'], 'Salon')
cyl(6.75, 11.42, 0.18, 0.35, 1.3, C['plant'], 'Salon')
box(2.8, 4.4, 10.2, 11.0, 0.68, 0.72, C['white'], 'Terrasse')
for x in (3.0, 4.2):
    box(x-0.04, x+0.04, 10.55, 10.65, -0.06, 0.68, C['black'], 'Terrasse')

label('GARAGE', 2.3, 0.75, 0.42)
label('WC', 5.85, 1.9, 0.22)
label('SDB', 7.2, 2.3, 0.28)
label('HALL', 6.1, 3.6, 0.28)
label('CHAMBRE 01', 10.0, 3.5, 0.32)
label('HALL / ENTRÉE', 3.6, 5.2, 0.32)
label('CUISINE', 3.2, 8.15, 0.36)
label('SÉJOUR', 7.7, 9.6, 0.42)
label('TERRASSE', 3.9, 9.85, 0.38, y=-0.048)

# =====================================================================
#                                ÉTAGE
# =====================================================================
PREFIX, YOFF = 'Etage_', H   # dalle de H à FL1, tout le reste mesuré depuis FL1
# --- Dalle (trémie d'escalier X 7.44-10.70, Z 4.45-5.90) ---
VX0, VX1, VZ0, VZ1 = 7.44, 10.70, 4.45, 5.90
slab_poly = (sbox(0, 0, 12.25, 4.45).union(sbox(1.42, 4.45, 10.95, 9.25))
             .union(sbox(6.2, 9.25, 10.95, 11.95)).difference(sbox(VX0, VZ0, VX1, VZ1)))
for p in (slab_poly.geoms if hasattr(slab_poly, 'geoms') else [slab_poly]):
    prism(p, 0, SLAB - 0.015, C['slab'], 'Dalle')
YOFF = FL1

# --- Murs ---
wall(0.87, 11.50, 0, 0.30, [(5.35, 5.90, 1.6, 2.2, 'win'), (6.50, 7.05, 1.6, 2.2, 'win')], color='stone')
wall(0.87, 1.17, 0.30, 4.10, [(1.45, 3.05, 0.9, 2.2, 'win')], color='stone')
wall(0.87, 1.75, 4.10, 4.43, color='stone')
wall(1.17, 4.91, 3.98, 4.10)                                             # chambre 02 / SDB parentale
wall(4.77, 4.88, 0.30, 3.98, [(3.10, 3.95, 0, DOOR, 'door')])           # chambre 02 / DEG
wall(4.88, 5.97, 1.22, 1.30)                                             # placard / WC
wall(5.97, 6.04, 0.30, 3.08)                                             # WC / SDB
wall(4.88, 7.42, 3.00, 3.08, [(5.05, 5.80, 0, DOOR, 'door'), (6.15, 7.10, 0, DOOR, 'door')])
wall(7.42, 7.50, 0.30, 4.25, [(3.34, 4.20, 0, DOOR, 'door')])           # DEG / chambre 03
wall(7.50, 11.50, 4.25, 4.43)
wall(11.20, 11.50, 0.30, 4.25, [(1.45, 3.05, 0.9, 2.2, 'win')], color='stone')
wall(4.91, 6.33, 4.10, 4.30)                                             # DEG / dégagement chambre 04
wall(1.42, 1.75, 4.43, 9.25, color='stone')
wall(4.80, 4.91, 4.10, 5.40, [(4.55, 5.30, 0, DOOR, 'door')])           # SDB parentale
wall(1.75, 4.91, 5.32, 5.40)
box(5.64, 6.26, 4.30, 5.75, 0, H, C['wall'], 'Murs')                     # gaine
box(5.64, 6.26, 8.60, 9.10, 0, H, C['wall'], 'Murs')                     # gaine
wall(6.20, 6.35, 4.30, 9.25, [(5.95, 6.85, 0, DOOR, 'door')])           # chambre 04 / salon
box(5.64, 6.33, 6.87, 7.45, -SLAB, H + 0.9, C['stone'], 'Cheminee')       # conduit de cheminée
wall(1.42, 6.35, 9.10, 9.25, [(4.05, 5.45, 0, 2.2, 'win')], color='stone')
wall(6.20, 6.35, 9.25, 11.95, [(9.85, 11.10, 0.9, 2.2, 'win')], color='stone')
wall(6.35, 10.95, 11.70, 11.95, [(7.90, 9.10, 0.9, 2.2, 'win')], color='stone')
wall(10.70, 10.95, 4.43, 11.70, color='stone')

for x, z in [(1.6,0.15),(6.19,0.15),(10.8,0.15),(1.6,4.3),(6.19,4.3),(10.8,4.3),
             (1.6,8.3),(6.19,8.3),(10.8,8.3),(6.19,11.8),(10.8,11.8)]:
    box(x-0.17, x+0.17, z-0.17, z+0.17, 0, H, C['column'], 'Poteaux')

# garde-corps de la trémie
for (xa, xb, za, zb) in [(VX0, VX0+0.05, VZ0, VZ1), (VX0, SX1, VZ1-0.05, VZ1)]:
    box(xa, xb, za, zb, 0.95, 1.0, C['wood'], 'Escalier')
    n = int(max(xb-xa, zb-za) / 0.12)
    for i in range(n+1):
        if xb-xa > zb-za: x = xa + i*(xb-xa)/n; box(x-0.012, x+0.012, za, zb, 0, 0.95, C['black'], 'Escalier')
        else:             z = za + i*(zb-za)/n; box(xa, xb, z-0.012, z+0.012, 0, 0.95, C['black'], 'Escalier')

# --- Sols ---
floor(1.17, 4.77, 0.30, 3.98, 'bed_floor', 'Chambre 02')
floor(4.88, 5.97, 1.30, 3.00, 'wet', 'WC')
floor(6.04, 7.42, 0.30, 3.00, 'wet', 'SDB')
floor(4.88, 7.42, 3.08, 4.10, 'hall', 'Degagement')
floor(6.33, 7.44, 4.10, 5.90, 'hall', 'Degagement')
floor(6.35, 10.70, 5.90, 11.70, 'living', "Salon d'etage")
floor(7.50, 11.20, 0.30, 4.25, 'bed_floor', 'Chambre 03')
floor(1.75, 4.80, 4.10, 5.32, 'wet', 'SDB parentale')
floor(4.91, 5.64, 4.30, 5.40, 'bed_floor', 'Chambre 04')
floor(1.75, 6.20, 5.40, 9.10, 'bed_floor', 'Chambre 04')

# --- Mobilier étage ---
box(4.88, 5.97, 0.30, 1.22, 0, 2.2, C['wood'], 'Mobilier')             # placard
bed(2.45, 4.00, 0.30, 2.30, 'bed2')
box(1.85, 2.35, 0.30, 0.75, 0, 0.55, C['wood'], 'Lit')
box(4.10, 4.60, 0.30, 0.75, 0, 0.55, C['wood'], 'Lit')
bed(8.55, 10.05, 0.30, 2.30, 'bed3')
box(7.95, 8.45, 0.30, 0.75, 0, 0.55, C['wood'], 'Lit')
box(10.15, 10.65, 0.30, 0.75, 0, 0.55, C['wood'], 'Lit')
box(10.60, 11.20, 2.90, 4.25, 0, 2.2, C['wood'], 'Armoire')
bed(2.55, 4.10, 5.45, 7.45, 'sofa')
box(1.90, 2.45, 5.45, 5.90, 0, 0.55, C['wood'], 'Lit')
box(4.20, 4.75, 5.45, 5.90, 0, 0.55, C['wood'], 'Lit')
box(5.20, 5.60, 1.30, 1.90, 0, 0.42, C['white'], 'Sanitaires')
box(5.20, 5.60, 1.30, 1.47, 0.42, 0.85, C['white'], 'Sanitaires')
box(7.00, 7.42, 1.55, 2.35, 0, 0.85, C['white'], 'Sanitaires')
box(6.60, 7.10, 0.32, 0.90, 0, 0.85, C['white'], 'Sanitaires')
box(3.25, 3.70, 4.10, 4.65, 0, 0.42, C['white'], 'Sanitaires')
box(4.15, 4.65, 4.10, 4.50, 0, 0.85, C['white'], 'Sanitaires')
box(1.80, 2.75, 4.12, 5.00, 0, 0.08, C['white'], 'Sanitaires')
box(2.73, 2.76, 4.12, 5.00, 0.08, 2.0, C['glass'], 'Sanitaires')
sofa_L(9.45, 10.40, 8.30, 11.00, 8.25)
box(8.50, 9.10, 8.75, 9.40, 0, 0.40, C['wood'], 'Salon')
box(6.40, 6.85, 7.80, 9.20, 0, 0.50, C['wood'], 'Salon')

label('CHAMBRE 02', 2.95, 3.35, 0.30)
label('WC', 5.43, 2.45, 0.22)
label('SDB', 6.75, 2.55, 0.26)
label('DÉG.', 6.15, 3.60, 0.24)
label('CHAMBRE 03', 9.35, 3.35, 0.30)
label('SDB', 3.95, 4.95, 0.22)
label('CHAMBRE 04', 3.30, 8.35, 0.32)
label("SALON D'ÉTAGE", 8.25, 7.00, 0.34)

# --- Toitures en tuiles (débords du RDC visibles sur le plan d'étage) ---
PREFIX, YOFF = 'Etage_', 0.0
slope(-0.30, 0.87, -0.30, 4.45, H + 0.55, H + 0.15, '-x', C['tile'], 'Toiture')
slope(-0.30, 1.42, 4.45, 8.70, H + 0.55, H + 0.15, '-x', C['tile'], 'Toiture')
slope(11.50, 12.55, -0.30, 4.75, H + 0.55, H + 0.15, '+x', C['tile'], 'Toiture')

# =====================================================================
scene = trimesh.Scene()
cache = {}
def srgb2lin(v): return v/12.92 if v <= 0.04045 else ((v+0.055)/1.055)**2.4
for gname, items in groups.items():
    by_col = defaultdict(list)
    for m, c in items: by_col[c].append(m)
    for k, (c, ms) in enumerate(by_col.items()):
        mesh = trimesh.util.concatenate(ms)
        if c not in cache:
            cache[c] = PBRMaterial(baseColorFactor=[int(round(srgb2lin(v)*255)) for v in c[:3]] + [int(c[3]*255)],
                                   metallicFactor=0.0, roughnessFactor=0.8,
                                   alphaMode='BLEND' if c[3] < 1 else 'OPAQUE', doubleSided=True)
        mesh.visual = trimesh.visual.TextureVisuals(material=cache[c])
        name = f'{gname}_{k}'.replace(' ', '_').replace("'", '')
        scene.add_geometry(mesh, node_name=name, geom_name=name)
scene.apply_translation([-6.125, 0, -5.975])
scene.export('../models/maison_3D.glb')
print('ok', len(scene.geometry))
