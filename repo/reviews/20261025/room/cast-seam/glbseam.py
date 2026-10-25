import struct, json, sys, numpy as np
b=open(sys.argv[1],'rb').read()
n=struct.unpack_from('<I',b,12)[0]; js=json.loads(b[20:20+n]); off=20+n; binc=b[off+8:off+8+struct.unpack_from('<I',b,off)[0]]
def acc(i):
    a=js['accessors'][i]; bv=js['bufferViews'][a['bufferView']]; o=bv.get('byteOffset',0)+a.get('byteOffset',0)
    nc={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]; dt={5126:np.float32,5123:np.uint16,5125:np.uint32,5121:np.uint8}[a['componentType']]
    it=np.dtype(dt).itemsize; st=bv.get('byteStride') or it*nc
    raw=np.frombuffer(binc[o:o+st*(a['count']-1)+it*nc],dtype=np.uint8)
    out=np.zeros((a['count'],nc),dt)
    for k in range(a['count']): pass
    idx=np.arange(a['count'])[:,None]*st+np.arange(it*nc)[None,:]
    return raw[idx].copy().view(dt).reshape(a['count'],nc)
print('nodes',[nd.get('name') for nd in js['nodes']][:12],'skins',len(js.get('skins',[])),'anims',[a.get('name') for a in js.get('animations',[])])
for m in js['meshes']:
  for p in m['primitives']:
    at=p['attributes']; P=acc(at['POSITION']); N=acc(at['NORMAL']); UV=acc(at['TEXCOORD_0']); I=acc(p['indices']).ravel()
    print(m.get('name'),'verts',len(P),'tris',len(I)//3,'bbox',P.min(0).round(3),P.max(0).round(3))
    key=np.round(P,5); u,inv,cnt=np.unique(key,axis=0,return_inverse=True,return_counts=True); inv=inv.ravel()
    dup=cnt[inv]>1
    print(' verts sharing a position',int(dup.sum()),'groups',int((cnt>1).sum()))
    # normal disagreement among dups
    order=np.argsort(inv); 
    bad=0; uvseam=0; worst=0
    groups={}
    for v in np.where(dup)[0]: groups.setdefault(inv[v],[]).append(v)
    angs=[]; pts=[]
    for g,vs in groups.items():
        nn=N[vs]; a=np.degrees(np.arccos(np.clip((nn[:,None,:]*nn[None,:,:]).sum(-1),-1,1))).max()
        angs.append(a); pts.append(P[vs[0]])
    angs=np.array(angs); pts=np.array(pts)
    print(' split-normal groups >2deg',int((angs>2).sum()),' >10deg',int((angs>10).sum()))
    cx=(P[:,0].min()+P[:,0].max())/2; w=P[:,0].max()-P[:,0].min()
    for ax,name in ((0,'x'),(2,'z')):
        c=(P[:,ax].min()+P[:,ax].max())/2; s=P[:,ax].max()-P[:,ax].min()
        mid=np.abs(pts[:,ax]-c)<0.02*s
        print(f'  dup groups on the {name}-midplane: {int(mid.sum())}, of them >2deg {int((mid&(angs>2)).sum())}')
    # geometric crease along x midplane: compare normals of nearby vertices across x=cx in the upper front
    h=P[:,1].max()-P[:,1].min()
