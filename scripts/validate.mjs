import fs from 'node:fs';
import assert from 'node:assert/strict';
import {Plant,simulate,defaults,metrics} from '../dist/model.js';
let ref=JSON.parse(fs.readFileSync(new URL('../dist/data/reference.json',import.meta.url))),plant=new Plant(ref.stc),worst=0;
for(let x of ref.checks){let r=plant.point(x.D,x.G,x.T,x.R,x.shade);for(let k of ['V','I','P']){let error=Math.abs(r[k]-x[k]);worst=Math.max(worst,error);assert(error<1e-5,`${k}: ${error}`)}let out=r.V/(1-x.D);assert(Math.abs(out*out/x.R-r.P)<1e-5)}
console.log('PASS: 25 original Python operating points, including shading; worst absolute error',worst,'; ideal power balance');
for(let i=0;i<5;i++){let rows=simulate(plant,defaults,i,ref.noise[0]);let m=metrics(rows),r=ref.table.filter(x=>x.scenario==='clean')[i];console.log(i,m);assert(Math.abs(m.ss/100-Number(r.eta_ss))<.0001);assert(Math.abs(m.eta/100-Number(r.eta_full))<.0001);assert(Math.abs(m.activity-Number(r.activity_index))<.003);assert(Math.abs(m.osc-Number(r.osc))<.0002);}
console.log('PASS: all 5 clean controller metrics agree with original project table');
for(let scenario of ['irradiance','temperature','load','rapid','burst','trap']){let o={...defaults,scenario,N:scenario==='burst'||scenario==='trap'?600:500,D0:scenario==='trap'?.65:.2};let rows=simulate(plant,o,4,ref.noise[0]);assert(rows.every(r=>Number.isFinite(r.P)&&r.D>=.1&&r.D<=.8));let states=new Set(rows.map(x=>x.stateUsed));console.log(scenario,[...states],metrics(rows).eta);if(scenario==='burst'){assert(states.has('SEARCH'));let lengths=[],n=0;for(let r of rows){if(r.stateUsed==='SEARCH')n++;else if(n){lengths.push(n);n=0}}assert(lengths.every(n=>n===15));}if(scenario==='trap')assert(rows.at(-1).P/rows.at(-1).pmpp<.8);}
console.log('PASS: dynamic profiles finite and bounded; SEARCH spans exactly 15 probes; local-peak limitation preserved');
