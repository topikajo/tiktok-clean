import json,zipfile,subprocess
from build_clean import ROOT,JAVA,CP,dex,path_for,FAMILIES
cs={'classes35.dex':['LX/1EAs;','LX/1EAt;','LX/1EBV;','Lcom/ss/android/ugc/aweme/account/login/authorize/AuthorizeActivity;'], 'classes44.dex':['LX/1Wvc;','LX/1Wve;','LX/1Wvg;'],'classes3.dex':['LX/04NS;','Lcom/bytedance/lobby/internal/LobbyCore;']}
root=ROOT/'analysis/auth-dispatch';root.mkdir(exist_ok=True)
with zipfile.ZipFile(path_for(FAMILIES['original'])) as z:
 for n,classes in cs.items():
  p=root/n;p.write_bytes(z.read(n));dex('disassemble',p,root/('smali-'+n[:-4]),*classes)
  with (root/(n+'.log')).open('w',encoding='utf8') as log:subprocess.run([str(JAVA),'-Xmx3g','-cp',CP,'SourceTool',str(p),str(root/'java'),*[c[1:-1].replace('/','.') for c in classes]],stdout=log,stderr=log,check=True,timeout=180)
