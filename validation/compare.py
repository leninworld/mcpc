"""Fail closed on incomplete coverage, new failures, or lost cases."""
from pathlib import Path
import json,sys,xml.etree.ElementTree as ET,tempfile

def cases(path):
 rows={}
 for c in ET.parse(path).getroot().iter('testcase'):
  key=c.get('classname','')+'::'+c.attrib['name'];original=key;occurrence=2
  while key in rows:key=original+' [occurrence '+str(occurrence)+']';occurrence+=1
  status='failed'if c.find('failure')is not None or c.find('error')is not None else 'skipped'if c.find('skipped')is not None else 'passed'
  rows[key]=status
 assert rows,'EMPTY_UNIT_SUITE';return rows
def assess(base,candidate,expected):
 assert set(base)<=set(candidate),'LOST_UNIT_CASE'
 added=set(candidate)-set(base);assert len(added)==len(expected)==10,'TEN_ADDED_CASES_REQUIRED'
 assert all(any(k.endswith(n)for k in added)for n in expected),'FOCUSED_NAME_MISMATCH'
 assert all(v!='failed'for v in base.values())and all(v!='failed'for v in candidate.values()),'UNIT_FAILURE'
 assert all(candidate[k]=='passed'for k in added),'ADDED_CASE_NOT_PASS'
 assert {k for k,v in base.items()if v=='skipped'}=={k for k,v in candidate.items()if v=='skipped'},'SKIP_DRIFT'
 return {'baseline_cases':len(base),'candidate_cases':len(candidate),'added_passed':len(added),'baseline_skipped':sum(v=='skipped'for v in base.values()),'candidate_skipped':sum(v=='skipped'for v in candidate.values())}
def e2e(base,candidate):
 assert base and set(base)==set(candidate),'E2E_COVERAGE_DRIFT'
 failures=lambda rows:{k for k,v in rows.items()if v['status']=='failed'}
 skips=lambda rows:{k for k,v in rows.items()if v['status']=='skipped'}
 assert failures(base)==failures(candidate)and failures(base)<={'basic/remote-open'},'E2E_FAILURE'
 assert skips(base)==skips(candidate),'E2E_SKIP_DRIFT'
 assert base['basic/help']['status']==candidate['basic/help']['status']=='passed','HELP_SUITE_NOT_PASS'
 return {'cases':len(base),'retained_failures':sorted(failures(base)),'skipped':sorted(skips(base))}
def fixture():
 expected=[f'new{i}'for i in range(10)];base={'old':'passed','skip':'skipped'};candidate=base|{n:'passed'for n in expected};assess(base,candidate,expected)
 for bad in [{k:v for k,v in candidate.items()if k!='old'},candidate|{'old':'failed'},candidate|{'new0':'skipped'}]:
  try:assess(base,bad,expected)
  except AssertionError:pass
  else:raise AssertionError('BAD_UNIT_ACCEPTED')
 rows={'basic/help':{'status':'passed'},'basic/remote-open':{'status':'failed'}};e2e(rows,rows)
 for bad in [rows|{'basic/help':{'status':'failed'}},{'basic/help':{'status':'passed'}}]:
  try:e2e(rows,bad)
  except AssertionError:pass
  else:raise AssertionError('BAD_E2E_ACCEPTED')
 with tempfile.TemporaryDirectory()as td:
  p=Path(td)/'unit.xml';p.write_text('<testsuites><testsuite><testcase classname="file" name="case"/></testsuite></testsuites>');assert cases(p)=={'file::case':'passed'}
 print('UNIT_E2E_XML_POSITIVE_NEGATIVE_FIXTURES_PASS')
if __name__=='__main__':
 if sys.argv[1:]==['--fixture']:fixture();sys.exit(0)
 root,out=map(Path,sys.argv[1:]);m=json.loads(Path('/inputs/manifest.json').read_text());r={'state':'INCOMPLETE'}
 try:
  r['unit']=assess(cases(root/'baseline-unit.xml'),cases(root/'candidate-unit.xml'),m['expected_terminal_cases'])
  r['e2e']={era:e2e(json.loads((root/('baseline-e2e-'+era+'.json')).read_text()),json.loads((root/('candidate-e2e-'+era+'.json')).read_text()))for era in ['legacy','modern']}
  cli=json.loads((root/'cli-comparison.json').read_text());assert cli['state']=='PASS';r['CLI']=cli
  r['state']='COMPLETE_FULL_UNIT_HELP_FORMATTING_AND_BOTH_BASIC_ERAS'
 except BaseException as error:r['error']=repr(error);raise
 finally:out.write_text(json.dumps(r,indent=2)+'\n')
