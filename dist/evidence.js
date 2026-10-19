import {defaults,Plant,simulate,metrics,names} from './model.js';
export const suite=[
 {id:'clean',label:'Clean baseline',options:{},seeds:1},
 {id:'step',label:'Irradiance 1000 → 700',options:{scenario:'irradiance'},seeds:1},
 {id:'rapid',label:'Rapid irradiance',options:{scenario:'rapid'},seeds:1},
 {id:'noise',label:'Noise σ = 1.5 W',options:{noise:1.5},seeds:8},
 {id:'burst',label:'8 W noise burst',options:{scenario:'burst',N:600},seeds:8},
 {id:'trap',label:'Shaded local-peak start',options:{scenario:'trap',D0:.65,N:600},seeds:1}
];
export function recovery(rows,start=0){for(let k=start;k<=rows.length-5;k++)if(rows.slice(k,k+5).every(r=>r.P/r.pmpp>=.99))return k-start;return null}
export function auditRun(rows){let maxBalance=0,minCCMMargin=Infinity;for(let r of rows){maxBalance=Math.max(maxBalance,Math.abs((r.V/(1-r.Dused))**2/r.R-r.P));minCCMMargin=Math.min(minCCMMargin,2*220e-6*45000/(r.Dused*(1-r.Dused))-r.R)}return {finite:rows.every(r=>['P','V','I','D','Dused','pmpp'].every(k=>Number.isFinite(r[k]))),bounded:rows.every(r=>r.D>=.1&&r.D<=.8&&r.Dused>=.1-1e-12&&r.Dused<=.8+1e-12),maxBalance,minCCMMargin}}
export function benchmark(ref,onProgress=()=>{}){const plant=new Plant(ref.stc),records=[];let done=0,total=suite.reduce((s,x)=>s+x.seeds*5,0);for(let test of suite){for(let type=0;type<5;type++){let samples=[];for(let seed=0;seed<test.seeds;seed++){let o={...defaults,...test.options,seed},rows=simulate(plant,o,type,ref.noise[seed]);samples.push({seed,...metrics(rows),recovery:recovery(rows,test.id==='step'?250:0),finalRatio:rows.at(-1).P/rows.at(-1).pmpp,searchProbes:rows.filter(r=>r.stateUsed==='SEARCH').length,audit:auditRun(rows)});onProgress(++done,total)}let mean=key=>samples.reduce((s,x)=>s+x[key],0)/samples.length;let eta=mean('eta'),sd=Math.sqrt(samples.reduce((s,x)=>s+(x.eta-eta)**2,0)/samples.length);records.push({case:test.id,label:test.label,controller:names[type],type,seeds:test.seeds,eta,sd,activity:mean('activity'),ss:mean('ss'),samples})}}return {schema:'mppt-benchmark-v2',createdAt:new Date().toISOString(),model:'Original quasi-static equations; browser recomputation',protocol:suite.map(t=>({...t,options:{...defaults,...t.options}})),records}}
// Same constant-input averaged boost ODE as source-model/boost_model/averaged_model.py.
// This experiment isolates the converter; it does not claim a coupled PV transient.
export function boostTransient({Vin=17.8,D0=.4,D1=.42,R=900/54.29,dt=2e-6}={}){
 if(![Vin,D0,D1,R,dt].every(Number.isFinite)||Vin<=0||R<=0||D0<.1||D0>.8||D1<.1||D1>.8||dt<=0||dt>1e-5)throw Error('Invalid boost experiment');
 const L=220e-6,C=671e-6,event=.05,end=.3,target=Vin/(1-D1),targetI=target/((1-D1)*R),stepCount=Math.ceil(end/dt),h=end/stepCount,skip=Math.max(1,Math.round(stepCount/1500));let v=Vin/(1-D0),i=v/((1-D0)*R),rows=[],minI=i,maxV=v,lastOutside=event,energyResidual=0;
 function rhs(i,v,d){return [(Vin-(1-d)*v)/L,((1-d)*i-v/R)/C]}
 function advance(span,d){let a=rhs(i,v,d),b=rhs(i+a[0]*span/2,v+a[1]*span/2,d),c=rhs(i+b[0]*span/2,v+b[1]*span/2,d),e=rhs(i+c[0]*span,v+c[1]*span,d);i+=span*(a[0]+2*b[0]+2*c[0]+e[0])/6;v+=span*(a[1]+2*b[1]+2*c[1]+e[1])/6}
 for(let k=0;k<=stepCount;k++){let t=k*h,d=t<event?D0:D1,min=rhs(i,v,d);energyResidual=Math.max(energyResidual,Math.abs(L*i*min[0]+C*v*min[1]-(Vin*i-v*v/R)));minI=Math.min(minI,i);maxV=Math.max(maxV,v);if(t>=event&&(Math.abs(v-target)>.01*target||Math.abs(i-targetI)>.01*targetI))lastOutside=t;if(k%skip===0||k===stepCount)rows.push({t:t*1000,V:v,I:i,D:d});if(k===stepCount)break;let next=(k+1)*h;if(t<event&&next>event){advance(event-t,D0);advance(next-event,D1)}else advance(h,d)}
 return {rows,target,targetI,minI,maxV,overshoot:Math.max(0,(maxV-target)/target*100),settlingMs:lastOutside>=end-h?null:Math.max(0,(lastOutside-event)*1000),ccm:minI>0,energyResidual,parameters:{Vin,D0,D1,R,L,C,dt:h,event,end}};
}
