import pathlib,re,json
plan=json.loads(pathlib.Path('analysis/build-plan.json').read_text(encoding='utf8'))
for family,entries in plan['families'].items():
 print(family)
 for d,e in entries.items():
  for p in pathlib.Path(e['patch_dir']).rglob('*.smali'):
   s=p.read_text(encoding='utf8')
   if 'FeedItemList' in p.name:
    m=re.search(r'(?m)^\.method[^\n]* getItems\(\)Ljava/util/List;\n.*?^\.end method',s,re.S|re.M)
    print(d,'feed_hooks',m.group(0).count('Lmod/clean/FeedAds;->filter'),'getter_return_count',m.group(0).count('return-object'))
   if p.name=='e.smali':print(d,'banner_worker_native',bool(re.search(r'(?m)^\.method.* native ',s)))
print('region replacements',sum(x.get('calls',0) for x in plan['changes']))
