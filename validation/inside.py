"""One owned Docker environment; upstream commands, no project execution on Mac."""
from pathlib import Path, PurePosixPath
import os,sys,json,subprocess,time,hashlib,tarfile,io,base64,urllib.request,resource,shutil,stat,socket
P=Path('/inputs');W=Path('/work');E=W/'evidence';E.mkdir(exist_ok=True)
M=json.loads((P/'manifest.json').read_text());I=json.loads((P/'source-inputs.json').read_text());B=json.loads((P/'bootstrap-metadata.json').read_text())
origin=int(os.environ['PACKET_ORIGIN']);end=origin+2700;F=E/'state.json'
state=json.loads(F.read_text())if F.exists()else {'state':'INCOMPLETE','origin':origin,'commands':[]}
home=W/'home';home.mkdir(exist_ok=True);os.environ['HOME']=str(home)
os.environ.update(PATH='/work/bin:'+os.environ['PATH'],XDG_CACHE_HOME='/work/cache',npm_config_cache='/work/npm-cache',GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1',CI='true')
for key in ['FORCE_COLOR','NO_COLOR','MCPC_JSON','MCPC_VERBOSE']:
 os.environ.pop(key,None)
def save():F.write_text(json.dumps(state,indent=2)+'\n')
def run(label,args,cwd=W,cap=600,allowed=(0,)):
 row={'label':label,'argv':list(map(str,args))};start=time.monotonic();remaining=min(cap,end-time.time()-180);assert remaining>0,'COMMON_DEADLINE'
 try:
  with (E/(label+'.stdout')).open('xb')as out,(E/(label+'.stderr')).open('xb')as err:
   r=subprocess.run(list(map(str,args)),cwd=cwd,stdout=out,stderr=err,timeout=remaining)
  row['exit']=r.returncode;assert r.returncode in allowed,(label,r.returncode)
 finally:
  row.update(seconds=time.monotonic()-start,cumulative_child_maxrss_KiB=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss);state['commands'].append(row);save()
def unpack(archive,root,prefix):
 assert not (root/prefix).exists(),'EXTRACTION_COLLISION'
 with tarfile.open(archive)as t:
  members=t.getmembers();assert len(members)<10000 and sum(x.size for x in members)<100*2**20,'ARCHIVE_BOUND'
  for m in members:
   p=PurePosixPath(m.name);assert not p.is_absolute()and '..'not in p.parts and p.parts[0]==prefix,'ARCHIVE_PATH'
   assert m.isdir()or m.isfile(),'ARCHIVE_KIND'
  for m in members:
   target=root/m.name
   if m.isdir():target.mkdir(parents=True,exist_ok=True)
   else:
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb')as out:shutil.copyfileobj(t.extractfile(m),out)
    target.chmod(m.mode&0o777)
 return root/prefix
def copy_regular_tree(source,target):
 skipped=[]
 def ignore(folder,names):
  bad=[]
  for name in names:
   path=Path(folder)/name;mode=path.lstat().st_mode
   if not (stat.S_ISREG(mode)or stat.S_ISDIR(mode)):bad.append(name);skipped.append(str(path.relative_to(source)))
  return bad
 shutil.copytree(source,target,ignore=ignore);return skipped
def fixtures():
 root=W/'evidence-fixture';root.mkdir();(root/'ordinary.txt').write_text('fixture')
 with socket.socket(socket.AF_UNIX)as sock:
  sock.bind(str(root/'bridge.sock'));skipped=copy_regular_tree(root,W/'evidence-fixture-copy')
  assert skipped==['bridge.sock'] and (W/'evidence-fixture-copy/ordinary.txt').read_text()=='fixture','SOCKET_COPY_FILTER'
 for variant in ['baseline','candidate']:
  root=W/('fixture-'+variant);root.mkdir();a=root/'tiny.tgz'
  with tarfile.open(a,'w:gz')as t:
   m=tarfile.TarInfo(variant+'/value');m.size=3;t.addfile(m,io.BytesIO(b'ok\n'))
  assert (unpack(a,root,variant)/'value').read_bytes()==b'ok\n'
 for name,kind in [('../escape','file'),('/absolute','file'),('bad/link','link')]:
  root=W/('negative-'+str(len(list(W.glob('negative-*')))));root.mkdir();a=root/'bad.tgz'
  with tarfile.open(a,'w:gz')as t:
   m=tarfile.TarInfo(name)
   if kind=='link':m.type=tarfile.SYMTYPE;m.linkname='../escape'
   else:m.size=1
   t.addfile(m,io.BytesIO(b'x')if kind=='file'else None)
  try:unpack(a,root,'bad')
  except AssertionError:pass
  else:raise AssertionError('UNSAFE_ARCHIVE_ACCEPTED')
def download(url,path,limit,algorithm,expected):
 with urllib.request.urlopen(url,timeout=30)as r:data=r.read(limit+1)
 assert len(data)<=limit,'BOOTSTRAP_BYTES'
 h=hashlib.new(algorithm,data).digest();assert h==expected,'BOOTSTRAP_HASH';path.write_bytes(data)
def fingerprints(variant):return {n:hashlib.sha256((W/variant/n).read_bytes()).hexdigest()for n in I[variant]['sourceFingerprints']}
try:
 phase=sys.argv[1]
 if phase=='prepare':
  fixtures();run('comparison-fixtures',['python3',P/'compare.py','--fixture'],cap=30)
  run('toolchain',['bash','-e','-c','node --version; npm --version; python3 --version; git --version; make --version; g++ --version; for executable in curl timeout ps pgrep openssl find sort sed awk grep cut tr head tail xargs date md5sum mktemp readlink chmod ln; do command -v \"$executable\"; done'],cap=30)
  version=subprocess.check_output(['node','-p','JSON.stringify(process.versions)'],text=True);state['node_versions']=json.loads(version);assert tuple(map(int,state['node_versions']['node'].split('.'))) >= (22,12,0)
  (W/'bin').mkdir();j=W/'bin/jq';download(B['jq']['browser_download_url'],j,3*2**20,'sha256',bytes.fromhex(B['jq']['digest'].split(':')[1]));j.chmod(0o755)
  a=W/'pnpm.tgz';download(B['pnpm']['dist']['tarball'],a,64*2**20,'sha512',base64.b64decode(B['pnpm']['dist']['integrity'].split('-',1)[1]));unpack(a,W,'package').rename(W/'pnpm');launcher=W/'bin/pnpm';launcher.write_text('#!/bin/sh\nexec node /work/pnpm/bin/pnpm.cjs \"$@\"\n');launcher.chmod(0o755)
  run('bootstrap-versions',['bash','-e','-c','jq --version; pnpm --version'],cap=30)
  for variant in ['baseline','candidate']:
   unpack(P/(variant+'.tar.gz'),W,variant);assert fingerprints(variant)==I[variant]['sourceFingerprints'],'SOURCE_HASH'
  assert (W/'baseline/pnpm-lock.yaml').read_bytes()==(W/'candidate/pnpm-lock.yaml').read_bytes()
  for variant in ['baseline','candidate']:
   args=['pnpm','install','--frozen-lockfile','--store-dir','/work/pnpm-store','--registry=https://registry.npmjs.org']
   if variant=='candidate':args.append('--offline')
   run(variant+'-install',args,W/variant,cap=600);assert (W/variant/'node_modules/tsx/dist/cli.mjs').is_file(),'LOCAL_TSX_REQUIRED_NO_NPX'
  state['prepare']='PASS';save()
 elif phase=='test':
  assert state['prepare']=='PASS'
  for variant in ['baseline','candidate']:
   s=W/variant
   run(variant+'-lint',['pnpm','run','lint'],s)
   run(variant+'-build',['pnpm','run','build'],s)
   run(variant+'-unit',['pnpm','run','test:unit','--reporter=default','--reporter=junit','--outputFile.junit='+str(E/(variant+'-unit.xml'))],s,cap=600)
   run(variant+'-reference',['pnpm','run','check:reference'],s)
   expected={str(f.relative_to(s/'test/e2e/suites')).removesuffix('.test.sh')for f in (s/'test/e2e/suites/basic').glob('*.test.sh')};assert expected
   for era in ['legacy','modern']:
    before=set((s/'test/runs').glob('*'))
    run(variant+'-e2e-'+era,['bash','test/e2e/run.sh','--no-build','--keep','--parallel','6','--server-protocol',era,'basic/'],s,cap=900,allowed=(0,1))
    created=set((s/'test/runs').glob('*'))-before;assert len(created)==1,'E2E_RUN_SCOPE';root=created.pop();rows={}
    for result in root.glob('basic/*/result'):
     key=str(result.parent.relative_to(root));code=int(result.read_text().strip());skipped=(result.parent/'.skipped').exists();rows[key]={'exit':code,'status':'failed'if code else 'skipped'if skipped else 'passed'}
    assert set(rows)==expected,'E2E_CASE_COVERAGE';(E/(variant+'-e2e-'+era+'.json')).write_text(json.dumps(rows,indent=2)+'\n')
    target=E/(variant+'-e2e-'+era+'-retained');state.setdefault('skipped_nonregular_evidence',[]).extend(copy_regular_tree(root/'basic',target));save()
   run(variant+'-last-lint',['pnpm','run','lint'],s)
   assert fingerprints(variant)==I[variant]['sourceFingerprints'],'SOURCE_DRIFT'
  run('help-and-formatters',['node',P/'compare-cli.mjs'],cap=300)
  run('compare-results',['python3',P/'compare.py',E,E/'comparison.json'],cap=30)
  state['state']='COMPLETE';save()
 else:raise AssertionError('UNKNOWN_PHASE')
except BaseException as error:state['error']=repr(error);save();raise
