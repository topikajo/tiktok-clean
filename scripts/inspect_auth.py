"""Compare the original login providers with the user's working mod providers."""
import pathlib,zipfile,json,subprocess
from build_clean import ROOT,FAMILIES,path_for,JAVA,CP,dex
root=ROOT/'analysis/auth-review';root.mkdir(parents=True,exist_ok=True)
report={}
for family,name in FAMILIES.items():
    apk=path_for(name);lookup={}
    for line in (ROOT/'analysis'/apk.stem/'classes.tsv').read_text(encoding='utf8').splitlines():
        fields=line.split('\t',1)
        if len(fields)==2:lookup[fields[1]]=fields[0]
    selected=[c for c in lookup if c.startswith('Lcom/bytedance/lobby/google/')]
    groups={}
    for c in selected:groups.setdefault(lookup[c],[]).append(c)
    report[family]=groups
    with zipfile.ZipFile(apk) as z:
        for n,cs in groups.items():
            dest=root/family/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(n))
            dex('disassemble',dest,root/family/('smali-'+n[:-4]),*cs)
            with (root/family/(n+'.jadx.log')).open('w',encoding='utf8') as log:
                subprocess.run([str(JAVA),'-Xmx3g','-cp',CP,'SourceTool',str(dest),str(root/family/'java'),*[c[1:-1].replace('/','.') for c in cs]],stdout=log,stderr=log,cwd=ROOT,check=True,timeout=180)
    print(family,len(selected),'Google provider classes inspected',flush=True)
(root/'groups.json').write_text(json.dumps(report,indent=2),encoding='utf8')
