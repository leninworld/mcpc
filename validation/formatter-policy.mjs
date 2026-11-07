import assert from 'node:assert/strict';
import {stripVTControlCharacters as strip} from 'node:util';

// These two contracts are already styled (or machine JSON) on upstream.
// Every other retained sample reaches a newly styled branch of this PR.
const unchanged = new Set(['formatJson', 'formatToolCallExample']);
export function verifyFormatter(name,before,after){
  assert.equal(strip(after),strip(before),'VISIBLE_FORMATTER_TEXT_DRIFT '+name);
  if(name!=='formatJson')assert(after.includes('\x1b'),'CANDIDATE_COLOR_MISSING '+name);
  if(unchanged.has(name))assert.equal(after,before,'UNCHANGED_CONTRACT_DRIFT '+name);
  else assert.notEqual(after,before,'EXPECTED_COLOR_DELTA '+name);
}
if(process.argv.includes('--fixture')){
  const cyan='\x1b[36mtext\x1b[39m';
  verifyFormatter('formatToolCallExample',cyan,cyan);
  verifyFormatter('formatJson','{"value":1}','{"value":1}');
  verifyFormatter('formatTools','text',cyan);
  for(const args of [
    ['formatToolCallExample',cyan,'text'],
    ['formatToolCallExample','text','text'],
    ['formatJson','{"value":1}','{"value":2}'],
    ['formatTools',cyan,cyan],
    ['formatTools','text','text'],
    ['formatTools','text','\x1b[36mother\x1b[39m'],
  ])assert.throws(()=>verifyFormatter(...args));
  console.log('FORMATTER_CHANGED_UNCHANGED_COLOR_AND_VISIBLE_TEXT_FIXTURES_PASS');
}
