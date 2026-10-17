import pathlib,subprocess,os,json
java=str(pathlib.Path(os.environ['JAVA_HOME'])/'bin/java.exe');cp='tools;tools/jadx/lib/jadx-1.5.6-all.jar'
classes={}
for l in pathlib.Path('analysis/integration-classes.tsv').read_text(encoding='utf8').splitlines():
 dex,c=l.split('\t')
 if ('/im/' in c and '/ecommerce/' not in c) or c.endswith('/AwemeHostApplication;') or c.endswith('/AccountService;') or c.endswith('/SettingContainerActivity;'):classes.setdefault(dex,[]).append(c)
for d,cs in classes.items():
 cmd=[java,'-Xmx3g','-cp',cp,'DexTool','disassemble','analysis/dex/integration/'+d,'analysis/integration-smali/'+d[:-4],*cs]
 subprocess.run(cmd,check=True)
print('disassembled',sum(map(len,classes.values())),flush=True)
