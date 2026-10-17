"""Observe ordinary guest startup on an owned AVD; never replace it with instrumentation."""
import argparse,hashlib,json,os,pathlib,re,subprocess,time,xml.etree.ElementTree as ET
root=pathlib.Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--serial',choices=['emulator-5582','emulator-5584'],default='emulator-5582');args=parser.parse_args()
adb=pathlib.Path(os.environ['LOCALAPPDATA'])/'Android/Sdk/platform-tools/adb.exe';package='com.zhiliaoapp.musically'
def run(*command,check=True,timeout=90):
    p=subprocess.run([str(adb),'-s',args.serial,*map(str,command)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
    output=p.stdout.decode('utf8','replace')
    if check and p.returncode:raise RuntimeError(output)
    return output
name='TikTokAudit32' if args.serial=='emulator-5582' else 'TikTokAuditArmNative'
assert name in run('emu','avd','name') and 'armeabi-v7a' in run('shell','getprop','ro.product.cpu.abilist')
assert run('shell','getprop','sys.boot_completed').strip()=='1','AVD is not booted'
build=json.loads((root/'release/arm32-build.json').read_text(encoding='utf8'))
path=run('shell','pm','path',package).strip().removeprefix('package:')
assert re.fullmatch(r'/data/app/[A-Za-z0-9_./=+~\-]+',path)
assert run('shell','sha256sum',path).split()[0]==build['sha256'],'Install the exact ARM32 release first'
run('shell','am','force-stop',package);run('logcat','-c')
launch=run('shell','am','start','-W','-n',package+'/com.ss.android.ugc.aweme.splash.SplashActivity',check=False)
first=run('shell','pidof',package,check=False).strip()
print('Native launch returned; observing guest for 30 seconds',flush=True)
time.sleep(30)
last=run('shell','pidof',package,check=False).strip();logs=run('logcat','-d','-v','brief')
prefix=root/'analysis'/('arm32-native-'+args.serial)
prefix.with_suffix('.launch.txt').write_text(launch,encoding='utf8');prefix.with_suffix('.logcat.txt').write_text(logs,encoding='utf8')
activities=run('shell','dumpsys','activity','activities');prefix.with_suffix('.activities.txt').write_text(activities,encoding='utf8')
ui_ok=False
try:
    remote='/sdcard/arm32-native-ui.xml';run('shell','uiautomator','dump',remote,timeout=45)
    ui=prefix.with_suffix('.ui.xml');run('pull',remote,ui)
    nodes=list(ET.parse(ui).iter('node'))
    ui_ok=any(n.get('package')==package for n in nodes) and not any(n.get('package') in ('com.android.permissioncontroller','com.google.android.permissioncontroller') for n in nodes)
except (RuntimeError,subprocess.TimeoutExpired,ET.ParseError):pass
bad_icu="Bad 'ubidi_openSized_66' call" in logs
passed='Status: ok' in launch and bool(first) and first==last and ui_ok and not bad_icu
baseline=root/'analysis/arm32-upstream-baseline-crash.txt'
baseline_icu=baseline.exists() and "Bad 'ubidi_openSized_66' call" in baseline.read_text(encoding='utf8')
observation={'avd':name,'api':run('shell','getprop','ro.build.version.sdk').strip(),'normal_startup_verified':passed,
             'observed_seconds':30,'same_process':bool(first) and first==last,'app_ui_observed':ui_ok,'arm_translation_icu_failure':bad_icu,
             'scope':'Guest native bootstrap; no account, feed playback or messages'}
report_path=root/'release/arm32-startup.json'
report=json.loads(report_path.read_text(encoding='utf8')) if report_path.exists() else {'apk_sha256':build['sha256'],'observations':[]}
assert report['apk_sha256']==build['sha256']
report['observations']=[r for r in report['observations'] if r['avd']!=name]+[observation]
report.update({'normal_startup_verified':any(o['normal_startup_verified'] for o in report['observations']),
               'physical_device_verified':False,'account_login_verified':False,
               'official_arm32_baseline':{'sha256':build['upstream_sha256'],'same_android11_translation_icu_failure':baseline_icu},
               'limitations':['ARM32 remains experimental until real ARMv7 phone validation','Plain-Application probes do not prove native startup','No real Google/email login, feed playback, camera or chat validation']})
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(observation,indent=2),flush=True)
