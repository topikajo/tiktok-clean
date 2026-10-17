import pathlib,zipfile,json,re
from audit_apks import Dex
for kind,name in [('central','TikTok_Central_v47.1.7_(MOD)'),('private','TikTok_Private_Plus_v47.1.7_(MOD)_arm8'),('platinum','TikTok_Platinum_v47.1.7_(MOD)_arm8'),('original','TikTok_47.1.4_original_apkpure')]:
 v=[];folder='originals' if kind=='original' else 'others'
 with zipfile.ZipFile(pathlib.Path(folder,name+'.apk')) as z:
  for n in z.namelist():
   if not re.fullmatch(r'classes(?:\d+)?\.dex',n):continue
   d=Dex(z.read(n))
   versions=[s for s in d.strings if re.fullmatch(r'\d{2}\.\d+\.\d+(?:_.*)?',s)]
   if versions:v.append((n,versions))
 pathlib.Path('analysis',kind+'-embedded-versions.json').write_text(json.dumps(v,indent=2),encoding='utf8');print(kind,v,flush=True)
