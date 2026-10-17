import pathlib,re
p=pathlib.Path('analysis/official-js/download.e5379114.js').read_text()
for term in ['APK','apk','onelink','Download','download','fetch','useApk','TikTokApk']:
 matches=list(re.finditer(re.escape(term),p));print('term',term,'count',len(matches))
 for m in matches[:8]:print(p[max(0,m.start()-80):m.start()+200])
