import pathlib,json,collections
s=json.loads(pathlib.Path('analysis/native-page-alignment.json').read_text())
print('central arm64 non16k:',[x['lib'] for x in s['TikTok_Central_v47.1.7_(MOD).apk'] if 'arm64' in x['lib']])
for kind in ['central','platinum','private']:
 p=pathlib.Path('analysis/decompiled',kind,'sources')
 print(kind,'native code classes',sum(' native ' in f.read_text(encoding='utf8') for f in p.rglob('*.java')))
