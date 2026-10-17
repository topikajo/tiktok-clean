import pathlib,collections,json,zipfile,re
root=pathlib.Path.cwd()
for kind,name,ds in [('central','TikTok_Central_v47.1.7_(MOD)',[33,35,36,37,38,39,40,41,42]),('private','TikTok_Private_Plus_v47.1.7_(MOD)_arm8',[42]),('platinum','TikTok_Platinum_v47.1.7_(MOD)_arm8',[1])]:
 d=root/'analysis'/name
 classes=[line.split('\t')[1] for line in (d/'classes.tsv').read_text(encoding='utf-8').splitlines()]
 tops=collections.Counter(c.split('/')[0] for c in classes)
 print(kind,'class_count',len(classes),'top',tops.most_common(25),flush=True)
 suspects=[l for l in (d/'classes.tsv').read_text(encoding='utf-8').splitlines() if re.search(r'L(?:me/|com/tiktok/plugin|com/tiktok/mod|tiktok/|com/batch/|com/mod/|com/central/)',l)]
 (root/'analysis'/f'{kind}-custom-classes.tsv').write_text('\n'.join(suspects),encoding='utf-8')
 print('custom',len(suspects),'sample',suspects[:7],flush=True)
 dest=root/'analysis'/'dex'/kind; dest.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(root/'others'/(name+'.apk')) as z:
  for i in ds:
   dex='classes.dex' if i==1 else f'classes{i}.dex'
   (dest/dex).write_bytes(z.read(dex))
  native=[n for n in z.namelist() if n.startswith('lib/')]
  (root/'analysis'/f'{kind}-libs.txt').write_text('\n'.join(native),encoding='utf-8')
