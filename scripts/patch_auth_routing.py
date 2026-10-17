"""Patch only Google provider selection, retain TikTok's browser OAuth and callback handling."""
import json,pathlib,re,zipfile,shutil
from build_clean import ROOT,FAMILIES,path_for,dex,source_class_path

plan_path=ROOT/'analysis/build-plan.json';plan=json.loads(plan_path.read_text(encoding='utf8'))
backup=ROOT/'analysis/previous-builds/clean1';backup.mkdir(parents=True,exist_ok=True)
for p in [ROOT/'output/TikTok_Clean_47.1.4_Universal.apk',plan_path,ROOT/'analysis/clean-manifest.axml',ROOT/'release/build-info.json',ROOT/'release/SHA256SUMS.txt']:
    if p.exists() and not (backup/p.name).exists():shutil.copy2(p,backup/p.name)

classes=['LX/1EAt;','LX/1EAs;'];name='classes35.dex'
source=path_for(FAMILIES['original']);original=ROOT/'analysis/build-inputs/original'/name
original.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(source) as z:original.write_bytes(z.read(name))
directory=ROOT/'patches/original/classes35'
entry=plan['families']['original'].get(name)
if entry is not None and any(c not in classes for c in entry['classes']):raise ValueError('Review existing DEX35 patches before replacing')
dex('disassemble',original,directory,*classes)

provider=source_class_path(directory,classes[0]);s=provider.read_text(encoding='utf8')
pattern=r'(?m)^\.method[^\n]* LJFF\(Ljava/lang/String;\)Ljava/lang/String;\n.*?^\.end method'
m=re.search(pattern,s,re.S|re.M)
if not m or '.registers 3' not in m.group(0):raise ValueError('Provider resolver no longer matches inspected base')
prefix='''
    invoke-static {p0}, Lmod/clean/AuthRouting;->providerOverride(Ljava/lang/String;)Ljava/lang/String;
    move-result-object v0
    if-eqz v0, :clean_original_provider
    return-object v0
    :clean_original_provider
'''
body=m.group(0).replace('    .registers 3\n','    .registers 3\n'+prefix,1)
provider.write_text(s[:m.start()]+body+s[m.end():],encoding='utf8')

controller=source_class_path(directory,classes[1]);s=controller.read_text(encoding='utf8')
m=re.search(r'(?m)^\.method[^\n]* LJIILL\(LX/1EAq;\)V\n.*?^\.end method',s,re.S|re.M)
if not m:raise ValueError('Third-party controller changed')
getter=r'(invoke-interface \{[^}]+\}, LX/1EAq;->getParameter\(\)Landroid/content/Intent;\n(?:(?!\s*move-result-object)[^\n]*\n)*?\s*move-result-object ([vp]\d+))'
body,n=re.subn(getter,lambda match:match.group(1)+'\n    invoke-static {'+match.group(2)+'}, Lmod/clean/AuthRouting;->normalizeIntent(Landroid/content/Intent;)V',m.group(0),count=1)
if n!=1:raise ValueError('Missing entry intent getter')
controller.write_text(s[:m.start()]+body+s[m.end():],encoding='utf8')

plan['families']['original'][name]={'input':str(original),'patch_dir':str(directory),'classes':classes}
plan['original_version_code']=2024701041
plan['auth_routing']='google-browser-provider; credential alias normalized; original OAuth verification retained'
plan['changes']=[c for c in plan['changes'] if c.get('change_id')!='google-browser-login']
plan['changes'].append({'change_id':'google-browser-login','family':'original','classes':classes,'change':'Prefer existing Google browser OAuth for Google/OneTap and preserve all non-Google auth paths, token exchange and server validation'})
plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
print('Google browser routing patches ready; original login APIs, callback and account checks retained.')
