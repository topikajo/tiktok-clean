"""Run installed-APK probes only on the task's disposable TikTokAudit AVD."""
import hashlib,json,os,pathlib,re,subprocess
root=pathlib.Path(__file__).resolve().parents[1]
adb=pathlib.Path(os.environ['LOCALAPPDATA'])/'Android/Sdk/platform-tools/adb.exe'
def run(*args,timeout=180):
    r=subprocess.run([str(adb),'-s','emulator-5580',*map(str,args)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
    text=r.stdout.decode('utf8','replace')
    if r.returncode:raise RuntimeError(text)
    return text
assert 'TikTokAudit' in run('emu','avd','name')
build=json.loads((root/'release/you-privacy-build.json').read_text(encoding='utf8'))
apk=pathlib.Path(build['file']);digest=hashlib.sha256(apk.read_bytes()).hexdigest();assert digest==build['sha256']
results={}
for name,pointer,component,log in [
 ('policy','you-probe-path.txt','mod.privacy.probe/mod.privacy.probe.PrivacyProbeInstrumentation','you-android-results.txt'),
 ('stress','you-stress-probe-path.txt','mod.privacy.stress/mod.privacy.stress.PrivacyStressInstrumentation','you-android-stress-fixed.txt'),
 ('updates','you-update-probe-path.txt','mod.privacy.updateprobe/mod.privacy.updateprobe.PrivacyUpdateInstrumentation','you-android-update-results.txt')]:
    probe=pathlib.Path((root/'analysis'/pointer).read_text(encoding='utf8').strip());print(run('install','-r',probe).strip(),flush=True)
    run('shell','am','force-stop','com.zhiliaoapp.musically')
    output=run('shell','am','instrument','-w','-r','-e','mode','fixed',component)
    (root/'analysis'/log).write_text(output,encoding='utf8')
    print(name+': '+output[-3500:],flush=True)
    assert 'INSTRUMENTATION_CODE: -1' in output and 'INSTRUMENTATION_RESULT: failure=' not in output and 'INSTRUMENTATION_FAILED' not in output,name
    results[name]={'passed':True,'log':log}
    if name=='stress':results[name]['result']=json.loads(re.search(r'INSTRUMENTATION_RESULT: stress_json=(\{[^\r\n]+\})',output)[1])
    else:results[name]['cases']=int(re.search(r'PASS (\d+)',output)[1])
(root/'release/you-android-checks.json').write_text(json.dumps({'apk_sha256':digest,'versionCode':build['versionCode'],'avd':'TikTokAudit','results':results},ensure_ascii=False,indent=2),encoding='utf8')
