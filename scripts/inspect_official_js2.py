import pathlib,re,json
p=pathlib.Path('analysis/official-js/download.e5379114.js').read_text()
for term in ['function K','var K','const K','https://','showApkTab','onClick','tt-download','download.tiktok']:
 for m in list(re.finditer(re.escape(term),p))[:10]:print(term,p[max(0,m.start()-80):m.start()+380])
