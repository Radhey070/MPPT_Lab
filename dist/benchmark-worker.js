import {benchmark} from './evidence.js';
self.onmessage=({data})=>{try{let result=benchmark(data,(done,total)=>self.postMessage({progress:done,total}));self.postMessage({result})}catch(e){self.postMessage({error:e.message})}};
