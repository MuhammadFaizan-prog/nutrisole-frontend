import {createServer} from 'vite';
import fs from 'node:fs/promises';
import path from 'node:path';
const root=process.cwd();
const mock=path.join(root,'scripts/figma-primitives.tsx');
const server=await createServer({configFile:false,server:{middlewareMode:true},plugins:[{name:'figma-source-adapter',enforce:'pre',resolveId(source,importer){if(importer?.includes('/src/nutrisole/')&&['./ui','./primitives','./ScenePhoto'].includes(source))return mock;}}]});
try{const {markup}=await server.ssrLoadModule('/scripts/figma-scenes-entry.tsx');await fs.mkdir('artifacts/figma',{recursive:true});await fs.writeFile('artifacts/figma/source-markup.json',JSON.stringify(markup,null,2));console.log('Exported six native UI scene trees; no browser or screenshots used.');}finally{await server.close();}
