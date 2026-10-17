"""Bound installed-APK checks to an owned ARM32-capable disposable AVD and actual APK bytes."""
import argparse,hashlib,json,os,pathlib,re,subprocess
root=pathlib.Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--serial',choices=['emulator-5582','emulator-5584','emulator-5586'],default='emulator-5582');args=parser.parse_args()
names={'emulator-5582':'TikTokAudit32','emulator-5584':'TikTokAuditArmNative','emulator-5586':'TikTokAudit32Api31'}
adb=pathlib.Path(os.environ['LOCALAPPDATA'])/'Android/Sdk/platform-tools/adb.exe'
def run(*args,timeout=240):
    result=subprocess.run([str(adb),'-s',parser_args.serial,*map(str,args)],capture_output=True,timeout=timeout)
    output=result.stdout.decode('utf8','replace')+result.stderr.decode('utf8','replace')
    if result.returncode:raise RuntimeError(output)
    return output
parser_args=args
assert names[args.serial] in run('emu','avd','name')
assert 'armeabi-v7a' in run('shell','getprop','ro.product.cpu.abilist')
report=json.loads((root/'release/arm32-build.json').read_text(encoding='utf8'))
apk=pathlib.Path(report['file'])
with apk.open('rb') as source:digest=hashlib.file_digest(source,'sha256').hexdigest()
assert digest==report['sha256']
for name,expected in report['source_sha256s'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
print(run('install','-r',apk).strip(),flush=True)
installed=run('shell','pm','path','com.zhiliaoapp.musically').strip().removeprefix('package:')
assert re.fullmatch(r'/data/app/[A-Za-z0-9_./=+~\-]+',installed),installed
assert run('shell','sha256sum',installed).split()[0]==digest,'Installed APK differs from checked file'
probe=pathlib.Path((root/'analysis/arm32-probe-path.txt').read_text(encoding='utf8').strip())
print(run('install','-r',probe).strip(),flush=True)
results={}
for name,klass in [('privacy_update','Arm32ProbeInstrumentation'),('legacy_bindings','Arm32LegacyProbeInstrumentation')]:
    run('shell','am','force-stop','com.zhiliaoapp.musically')
    output=run('shell','am','instrument','-w','-r','--abi','armeabi-v7a','mod.arm32.probe/mod.arm32.probe.'+klass)
    (root/'analysis'/('arm32-'+name+'-'+args.serial+'.txt')).write_text(output,encoding='utf8')
    print(output[-4500:],flush=True)
    assert 'INSTRUMENTATION_CODE: -1' in output and 'result=FAIL' not in output and 'INSTRUMENTATION_RESULT: failure=' not in output,name
    count=int(re.search(r'PASS (\d+)',output)[1]);results[name]={'passed':True,'cases':count}
    if name=='privacy_update':results[name]['reflection_100000_ms']=int(re.search(r'reflection_100000_ms=(\d+)',output)[1])
result={'apk_sha256':digest,'versionCode':report['versionCode'],'avd':names[args.serial],'serial':args.serial,
        'platform_api':run('shell','getprop','ro.build.version.sdk').strip(),'results':results,
        'actual_32bit_process_verified':True,'native_bootstrap_in_harness':False,'scope':'Installed Java helpers, real SDK models/PM/certificates/ABI and Android layout; native app startup checked separately; no live account or messages sent'}
with probe.open('rb') as stream:result['probe_sha256']=hashlib.file_digest(stream,'sha256').hexdigest()
result['test_source_sha256']={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['scripts/build_arm32_probe.py','scripts/test_arm32_android.py','tests/android/Arm32ProbeInstrumentation.java','tests/android/Arm32ProbeManifest.xml','tests/android/ProbeInstrumentation.java']}
(root/'release/arm32-android-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
