import sys, numpy as np
exec(open(sys.argv[2]).read().split("print('nodes'")[0])
for m in js['meshes']:
  for p in m['primitives']:
    at=p['attributes']; P=acc(at['POSITION']); N=acc(at['NORMAL']); UV=acc(at['TEXCOORD_0'])
    key=np.round(P,5); u,inv,cnt=np.unique(key,axis=0,return_inverse=True,return_counts=True); inv=inv.ravel()
    cx=(P[:,0].min()+P[:,0].max())/2; w=P[:,0].max()-P[:,0].min()
    groups={}
    for v in np.where(cnt[inv]>1)[0]: groups.setdefault(inv[v],[]).append(v)
    rows=[]
    for g,vs in groups.items():
        q=P[vs[0]]
        if abs(q[0]-cx)<0.03*w and q[2]>0.15 and 0.35<q[1]<0.95:
            nn=N[vs]; ang=np.degrees(np.arccos(np.clip((nn[:,None]*nn[None]).sum(-1),-1,1))).max()
            duv=np.abs(UV[vs][:,None]-UV[vs][None]).max()
            rows.append((round(float(q[1]),3),round(float(q[2]),3),round(float(ang),1),round(float(duv),3)))
    rows.sort()
    print(sys.argv[1].split('/')[-1],'front-centre seam groups',len(rows),'normal-split>2deg',sum(r[2]>2 for r in rows))
    print(' y,z,angle,uvjump:',rows[:40:3])
