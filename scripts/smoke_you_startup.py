"""Guest cold-start smoke on this task's disposable emulator, never a phone."""
import datetime, hashlib, json, os, pathlib, subprocess, time, xml.etree.ElementTree as ET

root = pathlib.Path(__file__).resolve().parents[1]
adb = pathlib.Path(os.environ['LOCALAPPDATA']) / 'Android/Sdk/platform-tools/adb.exe'
serial = 'emulator-5580'
package = 'com.zhiliaoapp.musically'
def run(*args):
    return subprocess.run([str(adb), '-s', serial, *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode('utf8', 'replace')
assert run('get-state').strip() == 'device'
run('shell', 'am', 'force-stop', package)
run('shell', 'am', 'force-stop', 'com.android.chrome')
run('logcat', '-c')
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
launch = run('shell', 'am', 'start', '-W', '-n', package + '/com.ss.android.ugc.aweme.splash.SplashActivity')
(root / 'analysis/you-final-launch.txt').write_text(launch, encoding='utf8')
assert 'Status: ok' in launch and 'LaunchState: COLD' in launch
pid = run('shell', 'pidof', package).strip()
assert pid
time.sleep(30)
assert run('shell', 'pidof', package).strip() == pid, 'Process died or restarted'
run('shell', 'uiautomator', 'dump', '/sdcard/you-final-ui.xml')
run('pull', '/sdcard/you-final-ui.xml', str(root / 'analysis/you-final-ui.xml'))
ui = ET.parse(root / 'analysis/you-final-ui.xml')
nodes = list(ui.iter('node'))
assert any(n.get('package') == package for n in nodes)
assert not any(n.get('package') == 'com.android.permissioncontroller' for n in nodes)
texts = [n.get('text', '') for n in nodes]
if any('birthdate' in s.lower() for s in texts):
    assert 'Кадр' not in texts, 'Frame action leaked into onboarding'
logs = run('logcat', '-d', '-v', 'brief')
(root / 'analysis/you-final-logcat.txt').write_text(logs, encoding='utf8')
assert 'dat=https://t.me' not in logs
assert not any('FATAL EXCEPTION' in s and '(' + pid + ')' in s for s in logs.splitlines())
activities = run('shell', 'dumpsys', 'activity', 'activities')
(root / 'analysis/you-final-activities.txt').write_text(activities, encoding='utf8')
assert any(package in s for s in activities.splitlines() if 'mResumedActivity' in s or 'topResumedActivity' in s)
run('shell', 'screencap', '-p', '/sdcard/you-final.png')
run('pull', '/sdcard/you-final.png', str(root / 'analysis/you-final.png'))
p = root / 'release/you-privacy-verification.json'
report = json.loads(p.read_text(encoding='utf8'))
build = json.loads((root / 'release/you-privacy-build.json').read_text(encoding='utf8'))
assert hashlib.sha256(pathlib.Path(build['file']).read_bytes()).hexdigest() == report['apk_sha256']
report['normal_startup'] = {'verified': True, 'serial': serial, 'started_at_utc': start,
                          'same_process_observed_seconds': 30, 'pid': pid,
                          'launch': 'COLD', 'unsolicited_permission_dialog': False,
                          'foreign_telegram_redirect': False,
                          'frame_action_on_onboarding': False,
                          'scope': 'Guest onboarding, no account or real video playback'}
p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
build['normal_startup_verified'] = True
(root / 'release/you-privacy-build.json').write_text(json.dumps(build, ensure_ascii=False, indent=2), encoding='utf8')
print('PASS guest cold-start: same process for 30s, no Telegram, no permission dialog, no frame action on onboarding')
