import zipfile,subprocess
from build_clean import ROOT,JAVA,CP,dex,FAMILIES,path_for
root=ROOT/'analysis/auth-old-dispatch';root.mkdir(exist_ok=True)
groups={'central':{'classes21.dex':['LX/0gsi;','LX/0gsY;','LX/0iC1;']},'platinum':{'classes35.dex':['LX/0oz5;','LX/0ozf;']}}
for family,dexes in groups.items():
 with zipfile.ZipFile(path_for(FAMILIES[family])) as z:
  for n,classes in dexes.items():
   p=root/family/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n));dex('disassemble',p,root/family/('smali-'+n[:-4]),*classes)
   with (root/family/(n+'.log')).open('w',encoding='utf8') as log:subprocess.run([str(JAVA),'-Xmx3g','-cp',CP,'SourceTool',str(p),str(root/family/'java'),*[c[1:-1].replace('/','.') for c in classes]],stdout=log,stderr=log,check=True,timeout=180)
