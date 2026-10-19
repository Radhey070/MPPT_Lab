"""Reproduce report baseline using unchanged project controllers; export numerical validation cases."""
import sys,json,csv
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'source-model/controllers'))
from coupling import _pv_model,operating_point,T_STC,R_LOAD_TYPICAL,iv_curve,mpp_from_curve
from po import POController
from vss_po import VSSPOController
from rls_vss import RLSVSSController
from hold_track import HoldTrackController
from full_controller import FullController
from coupling_shaded import shaded_operating_point
classes=[POController,VSSPOController,RLSVSSController,HoldTrackController,FullController]
out={'stc':_pv_model._STC_PARAMS,'noise':[np.random.default_rng(i).normal(size=1200).tolist() for i in range(8)],'reference':{},'checks':[]}
for j,cls in enumerate(classes):
 c=cls(D_init=.2,seed=0); rows=[]
 for k in range(500):
  d=c.D; state=getattr(c,'state','TRACK'); r=c.step_once(1000,T_STC,R_LOAD_TYPICAL)
  if isinstance(r,tuple):
   dn,v,i,p,ok=r[:5]; row=dict(D=dn,V=v,I=i,P=p,state='TRACK',confidence=None,theta_hat=None,perturbed=True)
  else: row={key:r.get(key) for key in ['D','V','I','P','state','confidence','theta_hat','perturbed']};row['state']=row['state'] or 'TRACK';row['perturbed']=True if row['perturbed'] is None else row['perturbed']
  row.update(Dused=d,stateUsed=state,k=k,G=1000,T=25,R=R_LOAD_TYPICAL);rows.append(row)
 out['reference'][str(j)]=rows
out['pmpp']=float(mpp_from_curve(*iv_curve(1000,T_STC))[2])
for g,t,r in [(1000,25,R_LOAD_TYPICAL),(700,45,12),(200,10,30),(1200,65,8)]:
 for d in [.1,.2,.4,.65,.8]:
  v,i,p,ok=operating_point(d,g,t+273.15,r);out['checks'].append(dict(D=d,G=g,T=t,R=r,V=v,I=i,P=p))
for d in [.1,.2,.4,.65,.8]:
 v,i,p,ok=shaded_operating_point(d,[1000,600,300],T_STC,R_LOAD_TYPICAL);out['checks'].append(dict(D=d,G=1000,T=25,R=R_LOAD_TYPICAL,V=v,I=i,P=p,shade=[1,.6,.3]))
out['table']=list(csv.DictReader(open(root/'dist/data/tables/ablation_summary.csv')))
(root/'dist/data/reference.json').write_text(json.dumps(out,default=lambda x:bool(x) if isinstance(x,np.bool_) else float(x),separators=(',',':')))
print('Exported original controller traces, panel fit, seeded noise and 25 operating-point checks')
