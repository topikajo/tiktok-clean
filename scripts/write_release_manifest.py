"""Export only verified APK metadata/checksums, never signing secrets."""
import pathlib,json,hashlib,re
root=pathlib.Path(__file__).resolve().parents[1]
results=json.loads((root/'analysis/build-results.json').read_text(encoding='utf8'))
probe=(root/'analysis/probe-final-results.txt').read_text(encoding='utf8')
plan=json.loads((root/'analysis/build-plan.json').read_text(encoding='utf8'))
android_checks=31 if plan.get('auth_routing') else 20
jvm_checks=45 if plan.get('auth_routing') else 33
assert 'result=PASS '+str(android_checks)+' checks' in probe,probe[-1000:]
assert sum(map(int,re.findall(r'PASS: (\d+)',(root/'analysis/compile-hooks.log').read_text(encoding='utf8'))))==jvm_checks
assert 'Status: ok' in (root/'analysis/final-cold-start.txt').read_text(encoding='utf8')
checks=json.loads((root/'analysis/output-class-verification.json').read_text(encoding='utf8'))
assert len(results)==len(checks)==6
rows=[];sums=[]
for r in results:
    p=pathlib.Path(r['file'])
    with p.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
    assert actual==r['sha256'],p
    relative=p.relative_to(root).as_posix()
    sums.append(actual+'  '+relative)
    rows.append({**r,'file':relative,'class_verification':next(c for c in checks if c['file']==p.name)})
release=root/'release';release.mkdir(exist_ok=True)
(release/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n',encoding='ascii')
(release/'build-info.json').write_text(json.dumps({'date':'2026-10-13','status':'experimental-phone-and-live-account-validation-pending','published':False,'update_feed_configured':False,'jvm_tests':jvm_checks,'android_harness_checks':android_checks,'auth_routing':plan.get('auth_routing'),'versionCode':plan.get('original_version_code',2024701040),'apks':rows},ensure_ascii=False,indent=2),encoding='utf8')
report=root/'AUDIT-RU.md';text=report.read_text(encoding='utf8').replace('359 890','359 888').replace('исполняет 17 проверок','исполняет 20 проверок')
report.write_text(text,encoding='utf8')
print('Six APK checksums verified and exported;',jvm_checks,'JVM and',android_checks,'Android harness checks; final cold launch OK.')
