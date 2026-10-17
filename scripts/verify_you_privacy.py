"""Independent final-file checks; emulator evidence is supplied separately."""
import hashlib, io, json, pathlib, re, zipfile
from elftools.elf.elffile import ELFFile
from you_native import patch as native_patch

root = pathlib.Path(__file__).resolve().parents[1]
report_path = root / 'release/you-privacy-build.json'
report = json.loads(report_path.read_text(encoding='utf8'))
apk = pathlib.Path(report['file'])
sha = hashlib.sha256(apk.read_bytes()).hexdigest()
assert sha == report['sha256'], 'Final APK differs from the build report'
with zipfile.ZipFile(report['source']) as source, zipfile.ZipFile(apk) as out:
    assert out.testzip() is None
    name = 'lib/arm64-v8a/libttmod.so'
    expected, edits = native_patch(source.read(name))
    assert out.read(name) == expected, 'Unaccounted native changes'
    libs = [n for n in out.namelist() if n.startswith('lib/') and n.endswith('.so')]
    assert len(libs) == 298
    elf_count = 0
    non_elf = []
    for entry in libs:
        data = out.read(entry)
        if entry != name:
            assert data == source.read(entry), entry
        if not data.startswith(b'\x7fELF'):
            non_elf.append(entry)
            continue
        elf_count += 1
        elf = ELFFile(io.BytesIO(data))
        for seg in elf.iter_segments():
            if seg['p_type'] == 'PT_LOAD':
                assert seg['p_align'] >= 16384, entry
                assert (seg['p_vaddr'] - seg['p_offset']) % 16384 == 0, entry
    auth = ['classes11.dex', 'classes32.dex']
    assert all(out.read(n) == source.read(n) for n in auth)
    bundle = out.read('assets/tty/bundled/classes.dex')
    meta = json.loads(out.read('assets/tty/bundled/manifest.json'))
    digest = hashlib.sha256(bundle).hexdigest()
    assert meta['targetDexSha256'] == meta['hashes']['classes.dex'] == meta['dexFiles'][0]['targetSha256'] == digest
    assert meta['targetSize'] == meta['dexFiles'][0]['targetSize'] == len(bundle)
    channel=json.loads(out.read('assets/clean-update-channel.json'))
    assert channel == json.loads((root/'assets/clean-update-channel.json').read_text(encoding='utf8'))
    assert channel['feeds'] == ['https://raw.githubusercontent.com/topikajo/tiktok-clean/updates/update.json']
policy = (root / 'analysis/you-policy-results.txt').read_text(encoding='utf8')
android = (root / 'analysis/you-android-results.txt').read_text(encoding='utf8')
policy_cases = int(re.search(r'PASS (\d+)', policy)[1])
android_cases = int(re.search(r'PASS (\d+) installed-APK harness cases', android)[1])
assert policy_cases >= 45
assert android_cases >= 30 and 'INSTRUMENTATION_CODE: -1' in android
installed_checks=json.loads((root/'release/you-android-checks.json').read_text(encoding='utf8'))
assert installed_checks['apk_sha256']==sha and installed_checks['versionCode']==report['versionCode']
assert all(r['passed'] for r in installed_checks['results'].values())
for name,digest in report['helper_source_sha256'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,'Source changed after build: '+name
for name,digest in report['build_inputs_sha256'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,'Build input changed: '+name
result = {
    'apk_sha256': sha,
    'jvm_policy_cases': policy_cases,
    'installed_apk_harness_cases': android_cases,
    'installed_updater_cases': installed_checks['results']['updates']['cases'],
    'installed_stress': installed_checks['results']['stress']['result'],
    'native_library_count': len(libs),
    'elf_library_count': elf_count,
    'non_elf_so_payloads_preserved': non_elf,
    'native_libraries_byte_identical_to_input': len(libs) - 1,
    'native_modified_instruction_bytes': sum(len(bytes.fromhex(e['after'])) for e in edits),
    'native_changes_accounted_for': True,
    'elf_16kb_page_alignment': True,
    'auth_dex_byte_identical_to_input': auth,
    'bundled_payload_hash_verified': True,
    'update_channel': channel,
    'normal_startup': {'verified': False, 'evidence': 'Must be completed separately from the harness'},
    'physical_device_verified': False,
    'account_login_verified': False,
    'live_feed_refresh_verified': False,
    'real_player_frame_capture_verified': False,
    'real_video_download_verified': False,
    'limitation': 'Harness uses plain Application. ARM64 hook engine is limited under emulator translation.'
}
(root / 'release/you-privacy-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
hashes = root / 'release/SHA256SUMS.txt'
lines = [s for s in hashes.read_text(encoding='utf8').splitlines() if 'TikTok_Clean_46.8.3_You_Privacy_ARM64.apk' not in s]
lines.insert(0, sha + '  output/' + apk.name)
hashes.write_text('\n'.join(lines) + '\n', encoding='utf8')
print(json.dumps(result, ensure_ascii=False, indent=2))
