import pathlib,re
for path,pattern in [('analysis/original-smali/classes4/com/ss/android/ugc/aweme/feed/model/FeedItemList.smali',r'getItems\(\)Ljava/util/List;'),('analysis/original-smali/classes2/com/ss/android/ugc/aweme/feed/model/Aweme.smali',r'isAd\(\)Z'),('analysis/original-smali/classes9/com/ss/android/ugc/aweme/experiment/CommentWithStickerExp.smali',r'.*')]:
 s=pathlib.Path(path).read_text(encoding='utf8');print(path)
 if pattern=='.*':print(s[:12000])
 else:
  for m in re.finditer(r'(?m)^\.method[^\n]*'+pattern+r'\n.*?^\.end method',s,re.S|re.M):print(m.group(0))
