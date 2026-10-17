import pathlib,re,json
p=pathlib.Path('analysis/official-desktop.html').read_text(encoding='utf-8')
for term in ['apk','downloadUrl','download_url','downloadAPK','Download APK','__UNIVERSAL_DATA_FOR_REHYDRATION__']:
 print('TERM',term)
 for m in list(re.finditer(re.escape(term),p,re.I))[:12]:print(p[max(0,m.start()-120):m.start()+230])
