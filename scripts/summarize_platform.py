import pathlib,json,collections
r=json.loads(pathlib.Path('analysis/native-page-alignment.json').read_text())
p=r['TikTok_Central_v47.1.7_(MOD).apk'];print('Central ARM64 below16k', [x['lib'] for x in p if 'arm64' in x['lib']])
lines=pathlib.Path('analysis/original-calls.tsv').read_text(encoding='utf8').splitlines()
tele=[l for l in lines if 'Landroid/telephony/TelephonyManager;' in l];pathlib.Path('analysis/original-telephony-calls.tsv').write_text('\n'.join(tele),encoding='utf8')
print('telephony-calls',len(tele),'dex',collections.Counter(l.split('\t')[0] for l in tele),'target-methods',collections.Counter(l.split('\t')[-1] for l in tele))
