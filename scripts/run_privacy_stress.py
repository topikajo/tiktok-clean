"""Reproducible, offline component load test. No traffic is sent to TikTok."""
import argparse, hashlib, json, os, pathlib, platform, shutil, subprocess, time

root=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('profile',choices=['baseline','fixed']);p.add_argument('--sessions',type=int,default=100000)
args=p.parse_args();out=root/'analysis/stress'/(args.profile+'-'+str(time.time_ns()));out.mkdir(parents=True)
snapshot=out/'source';shutil.copytree(root/'src/mod/privacy',snapshot)
java=pathlib.Path(os.environ['JAVA_HOME'])/'bin/java.exe';javac=java.with_name('javac.exe')
classes=out/'classes';classes.mkdir()
selected=['PrivacyNet.java','PermissionPolicy.java','RefreshPolicy.java','NativeRefresh.java']
if (snapshot/'CachedReflect.java').exists():selected.append('CachedReflect.java')
sources=[snapshot/name for name in selected]+list((root/'tests/stress/stubs').rglob('*.java'))+[root/'tests/stress/PrivacyStress.java']
with (out/'compile.log').open('w') as log:
    subprocess.run([str(javac),'--release','8','-encoding','UTF-8','-d',str(classes),*map(str,sources)],check=True,stdout=log,stderr=subprocess.STDOUT)
command=[str(java),'-Xms64m','-Xmx256m','-XX:+ExitOnOutOfMemoryError','-cp',str(classes),'PrivacyStress',str(args.sessions),str(out/'jvm.json')]
if args.profile=='fixed':command.append('strict')
started=time.monotonic()
with (out/'run.log').open('w') as log:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=240)
manifest={'profile':args.profile,'sessions':args.sessions,'exit_code':result.returncode,'wall_seconds':time.monotonic()-started,
          'source_sha256':{n:hashlib.sha256((snapshot/n).read_bytes()).hexdigest() for n in selected},
          'host':platform.platform(),'logical_cpus':os.cpu_count(),'heap_limit_mib':256,'result':str(out/'jvm.json')}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
(root/'analysis/stress'/('latest-'+args.profile+'.txt')).write_text(str(out),encoding='utf8')
print(json.dumps(manifest,indent=2),flush=True)
if (out/'jvm.json').exists():print((out/'jvm.json').read_text(encoding='utf8'),flush=True)
if result.returncode:print((out/'run.log').read_text(encoding='utf8')[-6000:],flush=True)
raise SystemExit(result.returncode)
