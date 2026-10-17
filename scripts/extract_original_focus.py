import pathlib,zipfile
names=['Lcom/ss/android/ugc/aweme/feed/model/FeedItemList;','Lcom/ss/android/ugc/aweme/feed/model/Aweme;','Lcom/ss/android/ugc/aweme/experiment/CommentWithStickerExp;','Lcom/ss/android/ugc/aweme/experiment/CommentWithStickerExp$CommentStickerConfig;']
lines=pathlib.Path('analysis/TikTok_47.1.4_original_apkpure/classes.tsv').read_text(encoding='utf8').splitlines();found={}
for l in lines:
 dex,c=l.split('\t')
 if c in names:found.setdefault(dex,[]).append(c)
print(found)
p=pathlib.Path('analysis/dex/original');p.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile('originals/TikTok_47.1.4_original_apkpure.apk') as z:
 for dex in found:(p/dex).write_bytes(z.read(dex))
pathlib.Path('analysis/original-focus.json').write_text(__import__('json').dumps(found),encoding='utf8')
