import pathlib,re,collections,zipfile,json
for kind,name in [('platinum','TikTok_Platinum_v47.1.7_(MOD)_arm8'),('private','TikTok_Private_Plus_v47.1.7_(MOD)_arm8')]:
 lines=pathlib.Path('analysis',name,'classes.tsv').read_text(encoding='utf8').splitlines()
 mod=[l for l in lines if re.search(r'L(?:mhmd/|me/tiktok|com/tiktok/plugin|īi/|com/jaggu/)',l)]
 pathlib.Path('analysis',kind+'-injected.tsv').write_text('\n'.join(mod),encoding='utf8')
 print(kind,'injected',len(mod),'dex',collections.Counter(l.split('\t')[0] for l in mod),'examples',mod[:12])
 with zipfile.ZipFile(pathlib.Path('others',name+'.apk')) as z:
  for dex in {l.split('\t')[0] for l in mod}:
   pathlib.Path('analysis','dex',kind,dex).write_bytes(z.read(dex))
