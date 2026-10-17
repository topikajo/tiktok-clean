import pathlib,json,collections
names={'central':'TikTok_Central_v47.1.7_(MOD)','platinum':'TikTok_Platinum_v47.1.7_(MOD)_arm8','private':'TikTok_Private_Plus_v47.1.7_(MOD)_arm8','original':'TikTok_47.1.4_original_apkpure'}
data={k:json.loads(pathlib.Path('analysis',v,'inventory.json').read_text(encoding='utf8')) for k,v in names.items()}
orig={e['name']:e for e in data['original']['entries']}
out={}
for kind in ['central','platinum','private']:
 entries={e['name']:e for e in data[kind]['entries']}
 same=[n for n in orig.keys() & entries.keys() if orig[n]['sha256']==entries[n]['sha256']]
 out[kind]={'same_entries':len(same),'entry_count':len(entries),'identical_native':sum(n.startswith('lib/') for n in same),'same_resources':sum(n.startswith('res/') for n in same)}
 classes={l.split('\t')[1] for l in pathlib.Path('analysis',names[kind],'classes.tsv').read_text(encoding='utf8').splitlines()}
 oclasses={l.split('\t')[1] for l in pathlib.Path('analysis',names['original'],'classes.tsv').read_text(encoding='utf8').splitlines()}
 focus=lambda c: '/comment/' in c and any(w in c.lower() for w in ['sticker','image','photo','voice','poll'])
 out[kind]['comment_media_classes']=len([c for c in classes if focus(c)])
 out[kind]['missing_original_named_comment_classes']=sorted(c for c in oclasses-classes if focus(c))
 pathlib.Path('analysis',kind+'-comment-media-classes.txt').write_text('\n'.join(sorted(c for c in classes if focus(c))),encoding='utf8')
 print(kind,{k:v for k,v in out[kind].items() if not isinstance(v,list)},'missing_named',len(out[kind]['missing_original_named_comment_classes']),flush=True)
print('original class_count',len(oclasses),'comment_media_named',len([c for c in oclasses if focus(c)]))
pathlib.Path('analysis/base-comparison.json').write_text(json.dumps(out,indent=2),encoding='utf8')
