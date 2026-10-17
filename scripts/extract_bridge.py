import pathlib,re,zipfile,json
look={c:d for d,c in (l.split('\t') for l in pathlib.Path('analysis/TikTok_47.1.4_original_apkpure/classes.tsv').read_text(encoding='utf8').splitlines())}
cs=['LX/0qFC;','LX/0qAl;','LX/0BVS;','LX/0BI4;','LX/03FI;','LX/0Bfl;','Lcom/ss/android/ugc/aweme/im/core/api/proxy/IIMCoreProxyService;','Lcom/ss/android/ugc/aweme/im/message/content/TextContent;']
cs += [c for c in look if 'IIMCoreProxyService;' in c or '/IAccountUserService;' in c or '/IMSDKClient;' in c]
groups={}
for c in sorted(set(cs)):
 if c in look:groups.setdefault(look[c],[]).append(c)
print(groups)
p=pathlib.Path('analysis/dex/bridge');p.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile('originals/TikTok_47.1.4_original_apkpure.apk') as z:
 for d in groups:(p/d).write_bytes(z.read(d))
pathlib.Path('analysis/bridge-extract.json').write_text(json.dumps(groups),encoding='utf8')
