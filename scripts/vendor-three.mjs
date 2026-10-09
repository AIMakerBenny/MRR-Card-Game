import {copyFileSync, mkdirSync, existsSync} from 'node:fs';
import {resolve} from 'node:path';
const src=resolve('node_modules/three/build/three.module.js');
const dest=resolve('vendor/three.module.js');
if (!existsSync(src)) throw new Error('three@0.160.1 not installed: run npm install first.');
mkdirSync(resolve('vendor'),{recursive:true});copyFileSync(src,dest);
console.log('Vendor Three.js 0.160.1 -> vendor/three.module.js');
