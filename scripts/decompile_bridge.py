import pathlib,json,subprocess,os
j=str(pathlib.Path(os.environ['JAVA_HOME'])/'bin/java.exe');cp='tools;tools/jadx/lib/jadx-1.5.6-all.jar'
for d,cs in json.loads(pathlib.Path('analysis/bridge-extract.json').read_text()).items():
 subprocess.run([j,'-Xmx3g','-cp',cp,'DexTool','disassemble','analysis/dex/bridge/'+d,'analysis/bridge-smali/'+d[:-4],*cs],check=True)
 with pathlib.Path('analysis/bridge-source.log').open('a',encoding='utf8') as f:
  subprocess.run([j,'-Xmx4g','-cp',cp,'SourceTool','analysis/dex/bridge/'+d,'analysis/bridge-java',*[c[1:-1].replace('/','.') for c in cs]],check=True,stdout=f,stderr=subprocess.STDOUT)
print('bridge sources done',flush=True)
