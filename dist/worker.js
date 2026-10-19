import {Plant,simulate,defaults,metrics} from './model.js';
let data,plant;
self.onmessage=({data:m})=>{try{if(m.init){data=m.init;plant=new Plant(data.stc);return}let o=m.options,isReference=Object.keys(defaults).every(k=>o[k]===defaults[k]);let runs=Array.from({length:5},(_,i)=>isReference?data.reference[i].map(r=>({...r,pmpp:data.pmpp})):simulate(plant,o,i,data.noise[o.seed]));self.postMessage({id:m.id,runs,metrics:runs.map(metrics),isReference})}catch(e){self.postMessage({id:m.id,error:e.message})}};
