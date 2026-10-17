"""Reject duplicate class definitions and test harness leakage in the final APKs."""
import pathlib,zipfile,re,json
from audit_apks import Dex
root=pathlib.Path(__file__).resolve().parents[1];results=[]
from build_clean import FAMILIES,path_for
for p in sorted((root/'output').glob('*.apk')):
    seen=set();duplicates=[];custom=[];leaked=[]
    with zipfile.ZipFile(p) as z:
        for n in z.namelist():
            if not re.fullmatch(r'classes\d*\.dex',n):continue
            for c in Dex(z.read(n)).classes:
                if c in seen:duplicates.append(c)
                seen.add(c)
                if c.startswith('Lmod/clean/'):custom.append(c)
                if c.startswith('Lmod/clean/probe/') or c.startswith('LFeedAdsTest') or c.startswith('LPolicyTest'):leaked.append(c)
    assert not duplicates,(p.name,duplicates)
    assert not leaked,(p.name,leaked)
    assert custom and all(c.startswith('Lmod/clean/') for c in custom)
    if p.name=='TikTok_Clean_47.1.4_Universal.apk':source=FAMILIES['original']
    else:source=p.name.replace('_Clean','_(MOD)')
    source_set=set()
    with zipfile.ZipFile(path_for(source)) as original:
        for n in original.namelist():
            if re.fullmatch(r'classes\d*\.dex',n):source_set.update(Dex(original.read(n)).classes)
    missing=sorted(source_set-seen)
    assert not missing,(p.name,'missing source classes',missing)
    results.append({'file':p.name,'classes':len(seen),'custom_classes':len(custom),'duplicates':duplicates,'test_class_leaks':leaked,'missing_source_classes':missing})
    print(p.name,len(seen),'classes;',len(custom),'helpers; no duplicate/test classes',flush=True)
(root/'analysis/output-class-verification.json').write_text(json.dumps(results,indent=2),encoding='utf8')
