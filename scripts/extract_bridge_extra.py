import pathlib,re,zipfile,subprocess,os
names=['Lcom/ss/android/ugc/aweme/IAccountService;','Lcom/ss/android/ugc/aweme/im/chatroom/api/model/EnterChatParams;','LX/0BVW;']
lookup={c:d for d,c in (l.split('\t') for l in pathlib.Path('analysis/TikTok_47.1.4_original_apkpure/classes.tsv').read_text(encoding='utf8').splitlines())}
g={}
for c in names:g.setdefault(lookup[c],[]).append(c)
with zipfile.ZipFile('originals/TikTok_47.1.4_original_apkpure.apk') as z:
 for d,cs in g.items():
  path=pathlib.Path('analysis/dex/bridge',d);path.write_bytes(z.read(d))
  subprocess.run([str(pathlib.Path(os.environ['JAVA_HOME'])/'bin/java.exe'),'-Xmx3g','-cp','tools;tools/jadx/lib/jadx-1.5.6-all.jar','DexTool','disassemble',str(path),'analysis/bridge-smali/'+d[:-4],*cs],check=True)
print(g)
