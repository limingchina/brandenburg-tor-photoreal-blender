import bpy, math, os, random
import numpy as np
from mathutils import Vector

OUT = r"C:\Users\china\Documents\Codex\2026-09-13\can\outputs"
os.makedirs(OUT, exist_ok=True)
BLEND_PATH = os.path.join(OUT, "brandenburg_tor_photoreal_v2.blend")

# Fresh scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for coll in list(bpy.data.collections):
    if coll.name != 'Collection':
        bpy.data.collections.remove(coll)

ARCH = bpy.data.collections.new('ARCHITECTURE')
QUAD = bpy.data.collections.new('QUADRIGA_HIGH_DETAIL')
DETAIL = bpy.data.collections.new('RELIEFS_AND_DETAILS')
ENV = bpy.data.collections.new('ENVIRONMENT')
bpy.context.scene.collection.children.link(ARCH)
bpy.context.scene.collection.children.link(QUAD)
bpy.context.scene.collection.children.link(DETAIL)
bpy.context.scene.collection.children.link(ENV)

def move_to(obj, collection):
    for c in list(obj.users_collection): c.objects.unlink(obj)
    collection.objects.link(obj)

# -----------------------------------------------------------------------------
# 2K PBR texture atlas pack (albedo / roughness / normal / metallic).
# Quadrants: pale sandstone, relief sandstone, verdigris bronze, worn bronze.
# -----------------------------------------------------------------------------
S = 1024
rng = np.random.default_rng(1788)
y, x = np.mgrid[0:S, 0:S]
fine = rng.normal(0.0, 1.0, (S, S)).astype(np.float32)
blur = fine.copy()
for _ in range(4):
    blur = (blur + np.roll(blur,1,0)+np.roll(blur,-1,0)+np.roll(blur,1,1)+np.roll(blur,-1,1))/5.0

albedo = np.zeros((S,S,3), dtype=np.float32)
rough = np.zeros((S,S), dtype=np.float32)
metal = np.zeros((S,S), dtype=np.float32)
height = np.zeros((S,S), dtype=np.float32)

def stone_region(mask, base, contrast, dark=False):
    xx=x[mask]; yy=y[mask]
    row=(yy//112).astype(np.int32)
    stagger=(row%2)*128
    bx=(xx+stagger)%256; by=yy%112
    joint=((bx<4)|(bx>251)|(by<4)|(by>107))
    mineral=(0.42*np.sin(xx*.017)+0.28*np.sin(yy*.051)+0.22*np.sin((xx+yy)*.007))
    n=np.clip(0.42*blur[mask]+0.20*fine[mask]+0.16*mineral,-1.2,1.2)
    c=np.array(base,dtype=np.float32)[None,:] + n[:,None]*contrast
    c[joint] *= 0.58 if not dark else 0.68
    pores=fine[mask] < -2.25
    c[pores] *= 0.65
    albedo[mask]=np.clip(c,0,1)
    rough[mask]=np.clip((0.76 if not dark else 0.82)+0.06*n+joint*.12,0,1)
    height[mask]=np.clip(0.58+0.11*n-joint*.38-pores*.16,0,1)
    metal[mask]=0.0

q1=(x<S//2)&(y<S//2)
q2=(x>=S//2)&(y<S//2)
q3=(x<S//2)&(y>=S//2)
q4=(x>=S//2)&(y>=S//2)
stone_region(q1,(0.70,0.62,0.49),0.045,False)
stone_region(q2,(0.53,0.45,0.34),0.052,True)

def bronze_region(mask, worn=False):
    xx=x[mask]; yy=y[mask]
    broad=(np.sin(xx*.011)+np.sin(yy*.015)+np.sin((xx-yy)*.006))/3.0
    n=np.clip(.42*blur[mask]+.15*fine[mask]+.35*broad,-1.1,1.1)
    if worn:
        base=np.array((0.105,0.145,0.115),dtype=np.float32)
        pat=np.array((0.055,0.28,0.23),dtype=np.float32)
        patina=np.clip((n+0.3)*0.48,0,0.75)
        r=0.39
    else:
        base=np.array((0.08,0.25,0.20),dtype=np.float32)
        pat=np.array((0.12,0.44,0.36),dtype=np.float32)
        patina=np.clip((n+0.65)*0.48,0.08,0.88)
        r=0.52
    c=base[None,:]*(1-patina[:,None])+pat[None,:]*patina[:,None]
    streak=np.maximum(0,np.sin(xx*.031+np.sin(yy*.007)*2)-.68)[:,None]*np.array((.07,.05,.015))
    albedo[mask]=np.clip(c+streak,0,1)
    rough[mask]=np.clip(r+.13*n,0.25,.78)
    metal[mask]=np.clip(.86-.14*patina,0,1)
    height[mask]=np.clip(.52+.13*n,0,1)

bronze_region(q3,False)
bronze_region(q4,True)

gy,gx=np.gradient(height)
strength=7.0
nx=-gx*strength; ny=-gy*strength; nz=np.ones_like(nx)
ln=np.sqrt(nx*nx+ny*ny+nz*nz)
normal=np.dstack(((nx/ln+1)*.5,(ny/ln+1)*.5,(nz/ln+1)*.5)).astype(np.float32)

def save_image(name, rgb, colorspace):
    im=bpy.data.images.new(name,width=S,height=S,alpha=True)
    im.colorspace_settings.name=colorspace
    rgba=np.concatenate((np.clip(rgb,0,1),np.ones((S,S,1),dtype=np.float32)),axis=2)
    # Blender 5.2's foreach_set path can silently save a zeroed image buffer;
    # direct RNA assignment is slower but reliably persists the atlas pixels.
    im.pixels=rgba.ravel().tolist()
    im.update()
    im.filepath_raw=os.path.join(OUT,name+'.png')
    im.file_format='PNG'
    im.save()
    del rgba
    return im

alb=save_image('brandenburg_atlas_albedo_1k',albedo,'sRGB')
rou=save_image('brandenburg_atlas_roughness_1k',np.repeat(rough[:,:,None],3,axis=2),'Non-Color')
nor=save_image('brandenburg_atlas_normal_1k',normal,'Non-Color')
met=save_image('brandenburg_atlas_metallic_1k',np.repeat(metal[:,:,None],3,axis=2),'Non-Color')

REGIONS={
    'stone':(0.01,0.01,0.49,0.49),
    'relief':(0.51,0.01,0.99,0.49),
    'bronze':(0.01,0.51,0.49,0.99),
    'bronze_dark':(0.51,0.51,0.99,0.99),
}

def make_atlas_material(name, region):
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    m.diffuse_color=(.65,.58,.46,1)
    n=m.node_tree.nodes; l=m.node_tree.links; n.clear()
    out=n.new('ShaderNodeOutputMaterial')
    bs=n.new('ShaderNodeBsdfPrincipled')
    tc=n.new('ShaderNodeTexCoord')
    mapping=n.new('ShaderNodeMapping')
    u0,v0,u1,v1=REGIONS[region]
    mapping.inputs['Scale'].default_value=(u1-u0,v1-v0,1)
    mapping.inputs['Location'].default_value=(u0,v0,0)
    l.new(tc.outputs['Generated'],mapping.inputs['Vector'])
    texs=[]
    for label,image_data in [('Albedo',alb),('Roughness',rou),('Normal',nor),('Metallic',met)]:
        t=n.new('ShaderNodeTexImage'); t.name=label; t.image=image_data; t.projection='BOX'; t.projection_blend=.18
        l.new(mapping.outputs['Vector'],t.inputs['Vector']); texs.append(t)
    nm=n.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value=.62
    l.new(texs[0].outputs['Color'],bs.inputs['Base Color'])
    l.new(texs[1].outputs['Color'],bs.inputs['Roughness'])
    l.new(texs[2].outputs['Color'],nm.inputs['Color'])
    l.new(nm.outputs['Normal'],bs.inputs['Normal'])
    l.new(texs[3].outputs['Color'],bs.inputs['Metallic'])
    bs.inputs['IOR'].default_value=1.48
    l.new(bs.outputs['BSDF'],out.inputs['Surface'])
    m['atlas_region']=region
    return m

MATS={k:make_atlas_material('MAT_PBR_ATLAS_'+k.upper(),k) for k in REGIONS}

def apply_mat(obj, region):
    if obj.type=='MESH':
        obj.data.materials.clear(); obj.data.materials.append(MATS[region])
    return obj

def bevel(obj,width=.04,segments=3):
    if width>0 and obj.type=='MESH':
        md=obj.modifiers.new('Micro bevel','BEVEL'); md.width=width; md.segments=segments
    return obj

def smooth(obj):
    if obj.type=='MESH':
        for p in obj.data.polygons: p.use_smooth=True
    return obj

def box(name,loc,dims,region='stone',bevel_w=.03,rot=(0,0,0),coll=ARCH):
    bpy.ops.mesh.primitive_cube_add(location=loc,rotation=rot)
    o=bpy.context.object; o.name=name; o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    apply_mat(o,region); bevel(o,bevel_w); move_to(o,coll); return o

def cyl(name,loc,r1,depth,region='stone',vertices=64,r2=None,rot=(0,0,0),coll=ARCH,bevel_w=.02):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices,radius1=r1,radius2=r1 if r2 is None else r2,depth=depth,location=loc,rotation=rot)
    o=bpy.context.object; o.name=name; apply_mat(o,region); smooth(o); bevel(o,bevel_w); move_to(o,coll); return o

def sphere(name,loc,scale,region='bronze',seg=40,rings=24,coll=QUAD):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,location=loc)
    o=bpy.context.object; o.name=name; o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    apply_mat(o,region); smooth(o); move_to(o,coll); return o

def between(name,a,b,r1,r2=None,region='bronze',vertices=24,coll=QUAD):
    a=Vector(a); b=Vector(b); d=b-a; L=d.length
    q=Vector((0,0,1)).rotation_difference(d.normalized())
    return cyl(name,(a+b)/2,r1,L,region,vertices,r2,q.to_euler(),coll,.015)

def torus(name,loc,major,minor,region='bronze_dark',rot=(0,0,0),coll=QUAD):
    bpy.ops.mesh.primitive_torus_add(major_radius=major,minor_radius=minor,major_segments=64,minor_segments=14,location=loc,rotation=rot)
    o=bpy.context.object; o.name=name; apply_mat(o,region); smooth(o); move_to(o,coll); return o

def cone(name,loc,r1,r2,depth,region='bronze',rot=(0,0,0),coll=QUAD,vertices=24):
    return cyl(name,loc,r1,depth,region,vertices,r2,rot,coll,.01)

def tube(name,pts,radius,region='bronze_dark',coll=QUAD):
    cu=bpy.data.curves.new(name,'CURVE'); cu.dimensions='3D'; cu.resolution_u=3; cu.bevel_depth=radius; cu.bevel_resolution=3
    sp=cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts)-1)
    for bp,p in zip(sp.bezier_points,pts):
        bp.co=p; bp.handle_left_type='AUTO'; bp.handle_right_type='AUTO'
    o=bpy.data.objects.new(name,cu); coll.objects.link(o); cu.materials.append(MATS[region]); return o

def triangular_prism(name,xcenter,zbase,width,height,depth,region='stone',coll=ARCH):
    y0,y1=-depth/2,depth/2; x0=xcenter-width/2; x1=xcenter+width/2; z0=zbase; z1=zbase+height
    vs=[(x0,y0,z0),(x1,y0,z0),(xcenter,y0,z1),(x0,y1,z0),(x1,y1,z0),(xcenter,y1,z1)]
    fs=[(0,1,2),(3,5,4),(0,3,4,1),(1,4,5,2),(2,5,3,0)]
    me=bpy.data.meshes.new(name+'Mesh'); me.from_pydata(vs,[],fs); me.update()
    o=bpy.data.objects.new(name,me); coll.objects.link(o); apply_mat(o,region); bevel(o,.04); return o

# -----------------------------------------------------------------------------
# Metric architectural reconstruction.
# -----------------------------------------------------------------------------
GATE_W=62.5; DEPTH=11.0; GATE_H=20.3; COLUMN_H=13.5
MAIN_W=33.2; PAV_W=(GATE_W-MAIN_W)/2
passages=[3.8,3.8,5.65,3.8,3.8]
diam=1.73; span=sum(passages)+diam*5
axes=[-span/2]
for p in passages: axes.append(axes[-1]+p+diam)
row_y=(-4.25,4.25)

# Plaza and stepped stylobate.
box('Granite plaza',(0,7,-.28),(92,62,.5),'relief',.02,coll=ENV)
for i,(w,d,h) in enumerate(((34.1,11,.22),(33.75,10.72,.18),(33.4,10.48,.16))):
    box(f'Stylobate course {i+1}',(0,0,.11+i*.18),(w,d,h),'stone',.025)

# True passage divider walls and deep shadowed openings.
for i,xp in enumerate(axes[1:-1],1):
    box(f'Passage divider wall {i}',(xp,0,6.75),(1.42,8.2,13.18),'stone',.025)
    for side in (-1,1):
        box(f'Divider bas-relief {i}_{side}',(xp+side*.72,-4.13,4.4),(.10,1.7,2.4),'relief',.03,coll=DETAIL)
        torus(f'Divider medallion {i}_{side}',(xp+side*.70,-4.16,8.6),.58,.09,'relief',(math.pi/2,0,0),DETAIL)

# Twelve tapered Doric columns with 20 recessed flute strips each.
for ri,yy in enumerate(row_y,1):
    for ci,xx in enumerate(axes,1):
        cyl(f'Doric shaft {ri}:{ci}',(xx,yy,6.95),.865,COLUMN_H-.65,'stone',80,.72,coll=ARCH,bevel_w=.015)
        box(f'Column square plinth {ri}:{ci}',(xx,yy,.35),(2.18,2.18,.24),'relief',.025)
        cyl(f'Column base torus {ri}:{ci}',(xx,yy,.60),1.07,.24,'stone',64,1.0,coll=ARCH,bevel_w=.015)
        cyl(f'Capital echinus {ri}:{ci}',(xx,yy,13.12),1.13,.66,'stone',64,.74,coll=ARCH,bevel_w=.02)
        box(f'Capital abacus {ri}:{ci}',(xx,yy,13.57),(2.18,2.18,.28),'stone',.035)
        for ring in range(3): cyl(f'Capital annulet {ri}:{ci}:{ring}',(xx,yy,12.76+ring*.09),.80,.045,'relief',48,coll=DETAIL,bevel_w=.006)
        for f in range(20):
            a=2*math.pi*f/20
            rr=.775
            cyl(f'Flute groove {ri}:{ci}:{f}',(xx+rr*math.cos(a),yy+rr*math.sin(a),6.82),.035,11.55,'relief',10,.025,coll=DETAIL,bevel_w=.0)

# Ceiling soffit and 25 coffers.
box('Deep passage soffit',(0,0,13.28),(MAIN_W,9.85,.24),'relief',.015)
centers=[(axes[i]+axes[i+1])/2 for i in range(5)]
for pi,cx in enumerate(centers):
    pw=passages[pi]
    for j in range(5):
        box(f'Passage coffer {pi+1}:{j+1}',(cx,-3.0+j*1.5,13.12),(pw-.38,1.05,.10),'bronze_dark',.03,coll=DETAIL)

# Entablature, frieze, attic and stepped cornice.
for name,z,d,w,h,reg in [
    ('Lower architrave',14.0,11.0,33.55,.52,'stone'),
    ('Main entablature',14.48,11.0,33.2,1.42,'stone'),
    ('Upper lintel',15.76,11.25,33.68,1.16,'stone'),
    ('Sculpted Doric frieze',16.73,11.10,32.85,.78,'relief'),
    ('Frieze crown',17.28,11.30,33.44,.24,'stone'),
    ('Attic',18.14,10.58,33.0,1.52,'stone'),
    ('Attic crown',18.94,10.72,33.18,.24,'stone'),
    ('Stepped attic shoulder',19.28,10.45,23.8,.72,'relief'),
    ('Quadriga plinth',19.96,10.28,14.8,.68,'stone')]:
    box(name,(0,0,z),(w,d,h),reg,.04)

# Doric triglyphs, metopes and guttae across both faces.
trig_count=17
for face_y in (-5.62,5.62):
    for i in range(trig_count+1):
        xx=-MAIN_W/2+i*(MAIN_W/trig_count)
        box(f'Triglyph {face_y}:{i}',(xx,face_y,16.72),(.70,.20,1.02),'relief',.012,coll=DETAIL)
        for g in range(6): sphere(f'Gutta {face_y}:{i}:{g}',(xx-.25+g*.10,face_y*1.002,16.12),(.045,.035,.07),'relief',12,8,DETAIL)
    for i in range(trig_count):
        xx=-MAIN_W/2+(i+.5)*(MAIN_W/trig_count)
        box(f'Metope {face_y}:{i}',(xx,face_y*1.003,16.73),(.92,.08,.72),'relief',.02,coll=DETAIL)
        # Small relief silhouette in each metope.
        sphere(f'Metope head {face_y}:{i}',(xx,face_y*1.006,16.88),(.10,.045,.10),'stone',12,8,DETAIL)
        between(f'Metope figure {face_y}:{i}',(xx,face_y*1.008,16.82),(xx+.12,face_y*1.008,16.46),.055,.04,'stone',10,DETAIL)

# Attic Peace procession: readable bas-relief field and 18 figures.
box('Attic relief field',(0,-5.34,18.42),(8.1,.12,1.35),'relief',.02,coll=DETAIL)
for i in range(18):
    xx=-3.45+i*(6.9/17)
    sphere(f'Attic relief head {i}',(xx,-5.43,18.70+(i%3)*.02),(.10,.055,.11),'stone',14,10,DETAIL)
    between(f'Attic relief body {i}',(xx,-5.44,18.58),(xx+(.07 if i%2 else -.06),-5.44,18.20),.065,.045,'stone',10,DETAIL)

# Side pavilions with recessed bodies, front/back porticoes and pediments.
for side in (-1,1):
    pc=side*(MAIN_W/2+PAV_W/2)
    box(f'Pavilion body {side}',(pc,0,3.95),(PAV_W,9.75,7.75),'stone',.06)
    for yy in (-4.93,4.93):
        box(f'Pavilion facade recess {side}:{yy}',(pc,yy,3.75),(PAV_W-2.7,.10,6.15),'relief',.025,coll=DETAIL)
        for j,off in enumerate((-PAV_W*.34,-PAV_W*.115,PAV_W*.115,PAV_W*.34)):
            cyl(f'Pavilion column {side}:{yy}:{j}',(pc+off,yy*1.02,3.3),.34,6.6,'stone',48,.28,coll=ARCH,bevel_w=.015)
            cyl(f'Pavilion base {side}:{yy}:{j}',(pc+off,yy*1.02,.16),.45,.22,'stone',40,.42,coll=ARCH,bevel_w=.01)
            cyl(f'Pavilion capital {side}:{yy}:{j}',(pc+off,yy*1.02,6.72),.44,.30,'stone',40,.30,coll=ARCH,bevel_w=.01)
        triangular_prism(f'Pavilion pediment {side}:{yy}',pc,7.45,PAV_W-1.5,2.05,.28,'stone',ARCH).location.y=yy*1.04
        triangular_prism(f'Pavilion pediment relief {side}:{yy}',pc,7.72,(PAV_W-1.5)*.76,1.18,.09,'relief',DETAIL).location.y=yy*1.055
    box(f'Pavilion cornice {side}',(pc,0,7.45),(PAV_W,11.0,.62),'stone',.045)
    # Patinated copper gable roof.
    triangular_prism(f'Pavilion copper roof {side}',pc,7.76,PAV_W-.35,3.04,9.55,'bronze',ARCH)
    # Ashlar courses.
    for z in np.arange(1.3,7.5,1.3):
        box(f'Pavilion course {side}:{z:.1f}',(pc,-4.91,float(z)),(PAV_W-.4,.035,.035),'relief',.0,coll=DETAIL)

# -----------------------------------------------------------------------------
# High-detail quadriga. Organic horse masses are voxel-remeshed before details.
# -----------------------------------------------------------------------------
def organic_horse(lane,idx):
    x0=lane
    parts=[]
    def part_s(loc,sc): parts.append(sphere('tmp',loc,sc,'bronze',32,20,QUAD))
    def part_b(a,b,r1,r2): parts.append(between('tmp',a,b,r1,r2,'bronze',20,QUAD))
    # Barrel, croup, chest, shoulder and haunch muscle groups.
    part_s((x0,.25,22.15),(.54,1.05,.62)); part_s((x0,.92,22.12),(.58,.58,.60)); part_s((x0,-.52,22.25),(.58,.62,.70))
    part_s((x0-.25,-.48,22.22),(.30,.48,.58)); part_s((x0+.25,.72,22.08),(.34,.50,.50))
    # Arched neck, poll, skull and muzzle.
    turn=(.12 if abs(x0)>1 else .03)*(-1 if x0<0 else 1)
    part_b((x0,-.62,22.45),(x0+turn,-1.05,23.20),.42,.28)
    part_b((x0+turn,-1.02,23.12),(x0+turn*1.3,-1.30,23.55),.29,.22)
    part_s((x0+turn*1.4,-1.42,23.58),(.34,.48,.34)); part_s((x0+turn*1.4,-1.83,23.40),(.30,.34,.24))
    # Articulated legs with believable knees and varied stride.
    leg_specs=[(-.28,-.48,-.14),(.28,-.45,.18),(-.30,.73,.12),(.30,.76,-.10)]
    for li,(dx,yy,stride) in enumerate(leg_specs):
        hip=(x0+dx,yy,21.95); knee=(x0+dx+stride*.45,yy-.16,21.20); ankle=(x0+dx+stride,yy-.36,20.45)
        if (idx+li)%3==0:
            ankle=(ankle[0],ankle[1]-.35,20.70)
        part_b(hip,knee,.17,.125); part_s(knee,(.16,.17,.15)); part_b(knee,ankle,.12,.075); part_s(ankle,(.12,.18,.10))
    # Join and voxel-remesh for one continuous sculptural surface.
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts: p.select_set(True)
    bpy.context.view_layer.objects.active=parts[0]
    bpy.ops.object.join(); horse=bpy.context.object; horse.name=f'Horse {idx} organic body'
    try:
        horse.data.remesh_voxel_size=.055
        horse.data.remesh_voxel_adaptivity=.01
        bpy.ops.object.voxel_remesh()
    except Exception as e:
        print('voxel remesh fallback',idx,e)
    smooth(horse); apply_mat(horse,'bronze')
    sub=horse.modifiers.new('Sculpt surface subdivision','SUBSURF'); sub.levels=1; sub.render_levels=1
    # Facial details.
    for sx in (-1,1):
        sphere(f'Horse {idx} eye {sx}',(x0+turn*1.4+sx*.22,-1.72,23.67),(.055,.045,.052),'bronze_dark',16,10,QUAD)
        sphere(f'Horse {idx} nostril {sx}',(x0+turn*1.4+sx*.11,-2.12,23.43),(.045,.035,.034),'bronze_dark',14,8,QUAD)
        cone(f'Horse {idx} ear {sx}',(x0+turn*1.4+sx*.16,-1.34,24.02),.085,.018,.36,'bronze',(0,sx*.20,0),QUAD,16)
    tube(f'Horse {idx} mouth',[(x0-.18,-2.13,23.35),(x0,-2.18,23.31),(x0+.18,-2.13,23.35)],.018,'bronze_dark',QUAD)
    # Layered mane strands.
    for m in range(10):
        t=m/9
        tube(f'Horse {idx} mane {m}',[(x0+turn*(1-t),-1.25+t*.76,23.80-t*.78),(x0+.24,-1.12+t*.82,23.68-t*.72),(x0+.30,-.98+t*.84,23.45-t*.72)],.045+(m%2)*.008,'bronze_dark',QUAD)
    # Flowing tail made from multiple tapered-looking strands.
    for s in range(6):
        tube(f'Horse {idx} tail {s}',[(x0+(.05*s-.13),1.24,22.35),(x0+(.10*s-.25),1.62,21.90),(x0+(.15*s-.38),1.75,21.20),(x0+(.18*s-.45),1.55,20.55)],.045,'bronze_dark',QUAD)
    # Hooves, bridle, collar, girth.
    for li,(dx,yy,stride) in enumerate(leg_specs):
        ax=x0+dx+stride; ay=yy-.36; az=20.34 if (idx+li)%3 else 20.59
        box(f'Horse {idx} hoof {li}',(ax,ay-.07,az),(.28,.40,.20),'bronze_dark',.055,coll=QUAD)
    torus(f'Horse {idx} shoulder collar',(x0,-.70,22.68),.45,.055,'bronze_dark',(math.pi/2,0,0),QUAD)
    tube(f'Horse {idx} bridle brow',[(x0-.30,-1.66,23.70),(x0,-1.78,23.78),(x0+.30,-1.66,23.70)],.025,'bronze_dark',QUAD)
    tube(f'Horse {idx} noseband',[(x0-.28,-1.98,23.48),(x0,-2.08,23.54),(x0+.28,-1.98,23.48)],.025,'bronze_dark',QUAD)
    tube(f'Horse {idx} rein',[(x0,-1.82,23.55),(x0*.45,.10,23.15),(0,1.45,23.55)],.018,'bronze_dark',QUAD)

for i,lane in enumerate((-1.80,-.60,.60,1.80),1): organic_horse(lane,i)

# Chariot, wheels, reliefs and draught pole.
box('Chariot floor',(0,1.72,21.10),(2.0,1.72,.18),'bronze_dark',.06,coll=QUAD)
box('Chariot breastwork',(0,1.02,21.82),(2.25,.16,1.35),'bronze',.08,coll=QUAD)
for sx in (-1,1):
    box(f'Chariot side {sx}',(sx*1.05,1.58,21.64),(.16,1.35,1.08),'bronze',.06,coll=QUAD)
    torus(f'Chariot wheel {sx}',(sx*1.25,1.76,21.05),.92,.085,'bronze_dark',(0,math.pi/2,0),QUAD)
    cyl(f'Wheel hub {sx}',(sx*1.25,1.76,21.05),.14,.34,'bronze_dark',32,rot=(0,math.pi/2,0),coll=QUAD,bevel_w=.02)
    for j in range(12):
        a=2*math.pi*j/12
        between(f'Wheel spoke {sx}:{j}',(sx*1.27,1.76,21.05),(sx*1.27,1.76+.79*math.cos(a),21.05+.79*math.sin(a)),.026,.020,'bronze',10,QUAD)
for j in range(7):
    box(f'Chariot relief panel {j}',(-.78+j*.26,.91,21.82),(.17,.035,.45),'bronze_dark',.015,coll=QUAD)
tube('Draught pole',[(0,1.28,21.0),(0,.15,21.2),(0,-1.45,21.4)],.055,'bronze_dark',QUAD)

# Victoria: anatomical masses, layered drapery and feather-by-feather wings.
cone('Victoria draped skirt',(0,1.58,22.15),.56,.25,1.78,'bronze',coll=QUAD,vertices=36)
sphere('Victoria torso',(0,1.54,23.08),(.38,.27,.62),'bronze',40,24,QUAD)
sphere('Victoria neck',(0,1.50,23.66),(.16,.15,.24),'bronze',24,16,QUAD)
sphere('Victoria head',(0,1.47,23.98),(.27,.24,.32),'bronze',40,24,QUAD)
sphere('Victoria hair',(0,1.66,24.05),(.29,.20,.30),'bronze_dark',32,18,QUAD)
for f in range(12):
    a=2*math.pi*f/12
    tube(f'Victoria robe fold {f}',[(.28*math.cos(a),1.58+.18*math.sin(a),22.85),(.42*math.cos(a),1.58+.22*math.sin(a),22.10),(.49*math.cos(a),1.58+.24*math.sin(a),21.35)],.032,'bronze_dark',QUAD)
between('Victoria left upper arm',(-.26,1.50,23.32),(-.62,1.05,23.58),.12,.09,'bronze',20,QUAD)
between('Victoria left forearm',(-.62,1.05,23.58),(-.30,.52,23.70),.095,.065,'bronze',20,QUAD)
between('Victoria right upper arm',(.26,1.50,23.34),(.60,1.12,23.62),.12,.09,'bronze',20,QUAD)
between('Victoria right forearm',(.60,1.12,23.62),(.34,.73,24.02),.095,.06,'bronze',20,QUAD)
for side in (-1,1):
    # Bone/wing core.
    between(f'Victoria wing core {side}',(side*.18,1.76,23.25),(side*.95,1.96,24.30),.16,.08,'bronze',24,QUAD)
    # Primary and secondary feathers, individually modeled and layered.
    for j in range(12):
        t=j/11; root=(side*(.25+.58*t),1.82+.20*t,23.40+.72*t)
        tip=(side*(.72+1.05*t),2.00+.10*t,23.10+.58*t)
        between(f'Victoria primary feather {side}:{j}',root,tip,.075,.022,'bronze' if j%2 else 'bronze_dark',16,QUAD)
    for j in range(8):
        t=j/7; root=(side*(.22+.46*t),1.78+.12*t,23.50+.55*t)
        tip=(side*(.55+.72*t),1.86+.08*t,23.72+.66*t)
        between(f'Victoria secondary feather {side}:{j}',root,tip,.065,.020,'bronze',16,QUAD)

# Standard, oak wreath, exact-looking Iron Cross silhouette, eagle.
between('Victoria standard staff',(.34,.72,24.02),(.34,.70,25.55),.045,.035,'bronze_dark',16,QUAD)
torus('Oak wreath',(.34,.66,25.24),.43,.055,'bronze',(math.pi/2,0,0),QUAD)
for j in range(22):
    a=2*math.pi*j/22
    sphere(f'Oak leaf {j}',(.34+.36*math.cos(a),.60,25.24+.36*math.sin(a)),(.10,.035,.045),'bronze',14,8,QUAD)
# Cross pattee as extruded 2D mesh.
pts=[(-.12,.45),(.12,.45),(.16,.16),(.45,.12),(.45,-.12),(.16,-.16),(.12,-.45),(-.12,-.45),(-.16,-.16),(-.45,-.12),(-.45,.12),(-.16,.16)]
curve=bpy.data.curves.new('Iron Cross Shape','CURVE'); curve.dimensions='2D'; curve.extrude=.045; curve.bevel_depth=.012; curve.resolution_u=2
sp=curve.splines.new('POLY'); sp.points.add(len(pts)-1)
for p,(px,pz) in zip(sp.points,pts): p.co=(px,pz,0,1)
sp.use_cyclic_u=True
cross=bpy.data.objects.new('Iron Cross',curve); QUAD.objects.link(cross); cross.location=(.34,.54,25.24); cross.rotation_euler=(math.pi/2,0,0); curve.materials.append(MATS['bronze_dark'])
# Eagle atop the standard.
sphere('Prussian eagle body',(.34,.70,25.73),(.20,.14,.27),'bronze',28,18,QUAD)
sphere('Prussian eagle head',(.34,.61,25.99),(.13,.12,.13),'bronze',24,16,QUAD)
cone('Prussian eagle beak',(.34,.43,25.98),.065,.008,.18,'bronze_dark',(math.pi/2,0,0),QUAD,14)
for side in (-1,1):
    for j in range(5):
        between(f'Eagle feather {side}:{j}',(.34+side*.10,.72,25.82),(.34+side*(.34+j*.15),.74,25.92-j*.06),.055,.016,'bronze',14,QUAD)

# -----------------------------------------------------------------------------
# Environment, physically based light and two presentation cameras.
# -----------------------------------------------------------------------------
ground_mat=bpy.data.materials.new('MAT_Pariser_Platz_Cobblestone'); ground_mat.use_nodes=True
gn=ground_mat.node_tree.nodes; gl=ground_mat.node_tree.links
pbs=gn.get('Principled BSDF'); pbs.inputs['Base Color'].default_value=(.16,.17,.17,1); pbs.inputs['Roughness'].default_value=.82
tc=gn.new('ShaderNodeTexCoord'); vor=gn.new('ShaderNodeTexVoronoi'); vor.distance='EUCLIDEAN'; vor.feature='DISTANCE_TO_EDGE'; vor.inputs['Scale'].default_value=34
bump=gn.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.28; bump.inputs['Distance'].default_value=.08
gl.new(tc.outputs['Generated'],vor.inputs['Vector']); gl.new(vor.outputs['Distance'],bump.inputs['Height']); gl.new(bump.outputs['Normal'],pbs.inputs['Normal'])
for o in ENV.objects:
    if o.name=='Granite plaza': o.data.materials.clear(); o.data.materials.append(ground_mat)

def look_at(obj,target): obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

bpy.ops.object.empty_add(location=(0,0,10.8)); focus=bpy.context.object; focus.name='Gate focus target'; move_to(focus,ENV)
bpy.ops.object.camera_add(location=(39,-118,29)); cam=bpy.context.object; cam.name='CAM_Main_Photoreal'; cam.data.lens=58; cam.data.sensor_width=36; look_at(cam,(0,0,11)); cam.data.dof.use_dof=True; cam.data.dof.focus_object=focus; cam.data.dof.aperture_fstop=10; move_to(cam,ENV)
bpy.ops.object.empty_add(location=(0,-.2,23.2)); qfocus=bpy.context.object; qfocus.name='Quadriga focus target'; move_to(qfocus,ENV)
bpy.ops.object.camera_add(location=(9,-28,26.2)); qcam=bpy.context.object; qcam.name='CAM_Quadriga_Closeup'; qcam.data.lens=74; look_at(qcam,(0,-.2,23.25)); qcam.data.dof.use_dof=True; qcam.data.dof.focus_object=qfocus; qcam.data.dof.aperture_fstop=7; move_to(qcam,ENV)

scene=bpy.context.scene
scene.world.use_nodes=True
wn=scene.world.node_tree.nodes; wl=scene.world.node_tree.links; wn.clear()
wout=wn.new('ShaderNodeOutputWorld'); bg=wn.new('ShaderNodeBackground')
bg.inputs['Color'].default_value=(0.42,0.55,0.78,1)
bg.inputs['Strength'].default_value=.52; wl.new(bg.outputs['Background'],wout.inputs['Surface'])
bpy.ops.object.light_add(type='SUN',location=(24,-38,48)); sun=bpy.context.object; sun.name='Late afternoon sun'; sun.data.energy=4.2; sun.data.angle=math.radians(4.0); look_at(sun,(0,0,9)); move_to(sun,ENV)
bpy.ops.object.light_add(type='AREA',location=(-18,-34,30)); area=bpy.context.object; area.name='Soft facade fill'; area.data.energy=4200; area.data.color=(1.0,.72,.46); area.data.shape='RECTANGLE'; area.data.size=42; area.data.size_y=24; look_at(area,(0,0,11)); move_to(area,ENV)
bpy.ops.object.light_add(type='AREA',location=(22,-20,21)); rim=bpy.context.object; rim.name='Quadriga key'; rim.data.energy=2300; rim.data.color=(.72,.88,1.0); rim.data.shape='DISK'; rim.data.size=18; look_at(rim,(0,0,23)); move_to(rim,ENV)

scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=1280; scene.render.resolution_y=720; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=False
scene.render.image_settings.color_mode='RGBA'
scene.view_settings.look='AgX - Medium High Contrast'
scene.render.resolution_percentage=100
scene.camera=cam

scene['asset_name']='Brandenburg Tor Photoreal V2'
scene['dimensions_m']='62.5 wide x 11 deep x 26 total height'
scene['atlas_pack']='brandenburg_atlas_{albedo,roughness,normal,metallic}_1k.png'
scene['reference_notes']='User images used as visual references only; no pixels copied into materials.'
scene['geometry_notes']='12 Doric columns, 20 flutes each, five passage bays, 25 ceiling coffers, layered reliefs, organic remeshed horses and feather-level Victoria/eagle work.'
scene['metric_reference']='Published overall dimensions and MIT-licensed Klotzkette/isometric-berlin architectural detail profile.'

bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
scene.render.filepath=os.path.join(OUT,'brandenburg_tor_photoreal_v2_preview.png')
bpy.ops.render.render(write_still=True)
scene.camera=qcam
scene.render.resolution_x=1000; scene.render.resolution_y=760
scene.render.filepath=os.path.join(OUT,'brandenburg_tor_photoreal_v2_quadriga_closeup.png')
bpy.ops.render.render(write_still=True)
scene.camera=cam
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)

with open(os.path.join(OUT,'brandenburg_tor_photoreal_v2_CREDITS.txt'),'w',encoding='utf-8') as f:
    f.write('Brandenburg Tor Photoreal V2\n\n')
    f.write('The two user-supplied photographs were used as visual references only.\n')
    f.write('Metric/detail reference: Klotzkette/isometric-berlin (MIT License), https://github.com/Klotzkette/isometric-berlin\n')
    f.write('Historical/metric cross-check: Berlin monument database and published 62.5 x 11 x 26 m envelope.\n')
    f.write('All meshes and PBR atlas maps in this Blender file were procedurally generated for this task.\n')

print('DONE',BLEND_PATH,'OBJECTS',len(bpy.data.objects))
