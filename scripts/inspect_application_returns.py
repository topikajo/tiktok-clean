import re,pathlib
s=pathlib.Path('patches/original/classes/com/ss/android/ugc/aweme/app/host/AwemeHostApplication.smali').read_text()
m=re.search(r'(?m)^\.method[^\n]* onCreate\(\)V\n.*?^\.end method',s,re.S|re.M);print('application normal returns',m.group(0).count('return-void'))
