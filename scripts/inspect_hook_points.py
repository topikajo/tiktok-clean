import pathlib,re
s=pathlib.Path('analysis/original.manifest.txt').read_text(encoding='utf8')
for m in re.finditer('FileProvider|fileprovider',s):print(s[max(0,m.start()-100):m.start()+450])
s=pathlib.Path('analysis/integration-smali/classes.dex/com/ss/android/ugc/aweme/app/host/AwemeHostApplication.smali').read_text(encoding='utf8')
m=re.search(r'(?m)^\.method[^\n]* onCreate\(\)V\n.*?^\.end method',s,re.S|re.M)
print('app onCreate start',m.group(0)[:250],'returns',m.group(0).count('return-void'))
p=pathlib.Path('analysis/bridge-smali/classes4/com/ss/android/ugc/aweme/im/chatroom/api/model/EnterChatParams.smali').read_text(encoding='utf8')
for sig in ['getSessionId','getUserId','getGroupId']:
 m=re.search(r'(?m)^\.method[^\n]* '+sig+r'\(\)Ljava/lang/String;\n.*?^\.end method',p,re.S|re.M);print(m.group(0))
