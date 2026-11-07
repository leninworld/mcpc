process.env.FORCE_COLOR='3';delete process.env.NO_COLOR;
import {execFileSync} from 'node:child_process';
import {readFileSync,writeFileSync} from 'node:fs';
import {stripVTControlCharacters as strip} from 'node:util';
import assert from 'node:assert/strict';
import {verifyFormatter} from './formatter-policy.mjs';
const E='/work/evidence';
const parser=await import('/work/candidate/dist/cli/parser.js');
const env=color=>({...process.env,FORCE_COLOR:color?'3':'0',NO_COLOR:color?undefined:'1',MCPC_JSON:'',MCPC_VERBOSE:''});
const run=(variant,args,color)=>execFileSync(process.execPath,['bin/mcpc',...args],{cwd:'/work/'+variant,encoding:'utf8',timeout:15000,env:env(color)});
function names(text){let commands=false;const out=[];for(const line of strip(text).split('\n')){if(/^Commands:/.test(line)){commands=true;continue;}if(/^\S/.test(line))commands=false;if(commands){const m=line.match(/^ {2}(\S+)/);if(m)out.push(m[1]);}}return out;}
const top=new Set([...parser.KNOWN_COMMANDS,...names(run('candidate',['--help'],false))]);
const session=new Set([...parser.KNOWN_SESSION_COMMANDS,...names(run('candidate',['@demo','--help'],false))]);
const commands=[['--help'],['@demo','--help'],...[...top].map(n=>['help',n]),...[...session].map(n=>['@demo',n,'--help'])];
const help=[];
for(const args of commands){const b=run('baseline',args,false),a=run('candidate',args,false),c=run('candidate',args,true);assert.equal(a,b);assert.equal(strip(c),b);assert.deepEqual(strip(c).split('\n').map(x=>x.length),b.split('\n').map(x=>x.length));help.push({args,plain:a,color:c});}
writeFileSync(E+'/help-captures.json',JSON.stringify(help,null,2)+'\n');
process.env.FORCE_COLOR='3';delete process.env.NO_COLOR;
const before=await import('/work/baseline/dist/cli/output.js');
const after=await import('/work/candidate/dist/cli/output.js');
const skill={uri:'skill://demo/SKILL.md',frontmatter:{name:'demo'},resources:[{uri:'skill://demo/SKILL.md',size:1},{uri:'skill://demo/references/example.md',size:4}]};
const content={data:Buffer.from('demo'),binary:true,mimeType:'application/octet-stream'};
const task={taskId:'demo-task',status:'completed',createdAt:'2026-01-01T00:00:00Z',lastUpdatedAt:'2026-01-01T00:00:00Z',ttlMs:1000,result:{structuredContent:{demo:true}}};
const samples=[
 ['formatTools',[[{name:'search',inputSchema:{type:'object'}}],{sessionName:'@demo'}]],
 ['formatToolCallExample',[{name:'search',inputSchema:{type:'object',properties:{query:{type:'string'}}}},'@demo']],
 ['formatResourceContents',['resource://demo',{contents:[{uri:'resource://demo',blob:'ZGVtbw=='}]},{sessionName:'@demo'}]],
 ['formatSkills',[[],'@demo']],['formatSkills',[[skill],'@demo']],
 ['formatSkillDetail',[skill,skill.uri,content,{sessionName:'@demo'}]],
 ['formatSkillDetail',[skill,'skill://demo/references/example.md',content,{sessionName:'@demo'}]],
 ['formatDirectoryChildren',['skill://demo',[{uri:'skill://demo/sub',name:'sub',mimeType:'inode/directory'}],'@demo']],
 ['formatDirectoryChildren',['skill://demo',[{uri:'skill://demo/a',name:'a',mimeType:'text/plain'}],'@demo']],
 ['formatCompletionResult',[{completion:{values:['hello']}},{ref:{type:'ref/prompt',name:'search'},argument:{name:'query',value:''}},'@demo']],
 ['formatCompletionResult',[{completion:{values:['hello']}},{ref:{type:'ref/resource',uri:'resource://{query}'},argument:{name:'query',value:''}},'@demo']],
 ['formatCompletionResult',[{completion:{values:['hello']}},{ref:{type:'ref/resource',uri:'resource://{query}/{other}'},argument:{name:'query',value:''}},'@demo']],
 ['formatTask',[task,{sessionName:'@demo'}]],
 ['formatTaskCommandsHint',['@demo','demo-task','working']],
 ['formatTaskCommandsHint',['@demo','demo-task','completed']],
 ['formatDiscoverResult',[{supportedVersions:['2026-07-28'],capabilities:{}},'@demo','2026-07-28']],
 ['formatServerDetails',[{serverInfo:{name:'demo',version:'1'},capabilities:{tools:{},resources:{subscribe:true},prompts:{},completions:{},tasks:{},logging:{}},protocolVersion:'2025-11-25'},'@demo']],
 ['formatJson',[{query:'hello',flag:true,n:3,none:null}]],
];
const results=[];
for(const [name,args]of samples){const b=await before[name](...args),a=await after[name](...args);verifyFormatter(name,b,a);results.push({name,args,before:b,after:a});}
const source=readFileSync('/work/candidate/src/cli/output.ts','utf8');
const row={state:'PASS',helpScreens:commands.length,formatterSamples:results.length,changedFormatterSamples:results.filter(r=>r.before!==r.after).length,commandHintOccurrences:(source.match(/commandHint\(/g)||[]).length,commandExampleOccurrences:(source.match(/commandExample\(/g)||[]).length,topCommands:[...top],sessionCommands:[...session]};
assert(results.length>0&&commands.length>0);writeFileSync(E+'/formatter-captures.json',JSON.stringify(results,null,2)+'\n');writeFileSync(E+'/cli-comparison.json',JSON.stringify(row,null,2)+'\n');console.log(JSON.stringify(row));
