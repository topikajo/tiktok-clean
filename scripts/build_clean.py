"""Reproducible, hash-pinned APK patches. Originals and native libraries are preserved.

prepare: disassemble only the classes that will change and write reviewable patches.
build: assemble those classes, merge into original DEX, repack, align and sign.
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import secrets
import shutil
import subprocess
import zipfile
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
SDK = pathlib.Path(os.environ.get('LOCALAPPDATA', 'C:/Users/robot/AppData/Local'))/'Android/Sdk'
JAVA = pathlib.Path(os.environ['JAVA_HOME'])/'bin/java.exe'
BT = SDK/'build-tools/36.1.0'
CP = str(ROOT/'tools')+os.pathsep+str(ROOT/'tools/jadx/lib/jadx-1.5.6-all.jar')
EXPECTED = {
    'TikTok_Central_v47.1.7_(MOD).apk':'bb93b32bcaf4b488e1396e8d274124f9fc6114e99c498afddd0b7559b4ebacf5',
    'TikTok_Platinum_v47.1.7_(MOD)_arm7.apk':'bf99c34ef235ef7b56284ffe750a96c8d40c3b2e7c3ca1ce7fd085df32df4151',
    'TikTok_Platinum_v47.1.7_(MOD)_arm8.apk':'72b39076c6d1ab056617fa6e2c76003214d317c9170964fc90c5ee99cbbc7cfd',
    'TikTok_Private_Plus_v47.1.7_(MOD)_arm7.apk':'622f078330cc90b8abf2011438d3d8d31fb52bf61d2db5f79fc312be0efe867d',
    'TikTok_Private_Plus_v47.1.7_(MOD)_arm8.apk':'ce26ebb3e28fff15a399c9c86eb6376b2fb9d416f7933a57c1cbf1a0f8ae6b69',
    'TikTok_47.1.4_original_apkpure.apk':'4226ed5d3031b68208c29f62d80ac421b281fc74201bc4163d98e442d0991a40',
}
FAMILIES = {
    'central':'TikTok_Central_v47.1.7_(MOD).apk',
    'platinum':'TikTok_Platinum_v47.1.7_(MOD)_arm8.apk',
    'private':'TikTok_Private_Plus_v47.1.7_(MOD)_arm8.apk',
    'original':'TikTok_47.1.4_original_apkpure.apk',
}
FEED = 'Lcom/ss/android/ugc/aweme/feed/model/FeedItemList;'
STICKER = 'Lcom/ss/android/ugc/aweme/experiment/CommentWithStickerExp;'

def run(args):
    print('RUN', ' '.join(str(a) for a in args), flush=True)
    subprocess.run([str(a) for a in args],cwd=ROOT,check=True,timeout=600)

def dex(*args):
    if args[0]=='disassemble' and len(args)>3:
        descriptors=ROOT/'analysis/disassemble-descriptors.json'
        descriptors.write_text(json.dumps(list(args[3:]),ensure_ascii=False),encoding='utf8')
        args=(*args[:3],'@'+str(descriptors))
    run([JAVA,'-Xmx4g','-cp',CP,'DexTool',*args])

def path_for(name):
    return ROOT/('originals' if name.startswith('TikTok_47.') else 'others')/name

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def verify_source(name):
    p=path_for(name)
    if sha(p)!=EXPECTED[name]:raise ValueError('Unexpected input hash: '+name)
    return p

def replace_method(text, signature, body):
    # Require a token boundary before the complete name. A lancet wrapper may end in "onEvent" too.
    pattern=r'(?m)^\.method (?P<flags>(?:[^ \n]+ )*)(?P<sig>'+re.escape(signature)+r')\n.*?^\.end method'
    matches=list(re.finditer(pattern,text,re.S|re.M))
    if len(matches)!=1:raise ValueError('Expected exactly one method: '+signature)
    m=matches[0]
    flags=m.group('flags').replace('native ','')
    return text[:m.start()]+'.method '+flags+signature+'\n'+body+'\n.end method'+text[m.end():]

def source_class_path(directory, descriptor):
    normal=directory/(descriptor[1:-1]+'.smali')
    if normal.exists():return normal
    for p in directory.rglob('*.smali'):
        if descriptor in p.read_text(encoding='utf8').splitlines()[0]:return p
    raise FileNotFoundError(descriptor)

def prepare(region):
    all_plans={}
    changes=[]
    for family,name in FAMILIES.items():
        apk=verify_source(name)
        lookup={c:d for d,c in (l.split('\t') for l in (ROOT/'analysis'/apk.stem/'classes.tsv').read_text(encoding='utf8').splitlines())}
        selected={FEED}
        if family=='original':
            selected.add(STICKER)
            if region:
                for line in (ROOT/'analysis/original-telephony-calls.tsv').read_text(encoding='utf8').splitlines():
                    _,method,_,_,target=line.split('\t')
                    if target.endswith(')Ljava/lang/String;'):selected.add(method.split('->')[0])
        else:
            selected.update({'Lme/tiktokupdatez/f/a;','Lme/tiktokupdatez/f/e;','Lme/tiktokupdatez/f/h;'})
            if family=='central':selected.add('Lcom/tiktok/plugin/client/ClientSettings$CommentWithSticker;')
        grouped=defaultdict(list)
        for c in sorted(selected):grouped[lookup[c]].append(c)
        plans={}
        with zipfile.ZipFile(apk) as z:
            for dex_name,classes in grouped.items():
                original=ROOT/'analysis/build-inputs'/family/dex_name
                original.parent.mkdir(parents=True,exist_ok=True);original.write_bytes(z.read(dex_name))
                patchdir=ROOT/'patches'/family/dex_name.replace('.dex','')
                if patchdir.exists():raise FileExistsError('Reviewable patches already exist: '+str(patchdir))
                dex('disassemble',original,patchdir,*classes)
                plans[dex_name]={'input':str(original),'patch_dir':str(patchdir),'classes':classes}
        all_plans[family]=plans

        feedpath=source_class_path(pathlib.Path(plans[lookup[FEED]]['patch_dir']),FEED)
        text=feedpath.read_text(encoding='utf8')
        getter=re.search(r'(?m)^\.method[^\n]* getItems\(\)Ljava/util/List;\n.*?^\.end method',text,re.S|re.M)
        if not getter or ' native ' in getter.group(0):raise ValueError('Cannot safely patch feed getter')
        body,n=re.subn(r'(?m)^(\s*)return-object ([vp]\d+)\s*$',lambda m:m.group(1)+'invoke-static {'+m.group(2)+'}, Lmod/clean/FeedAds;->filter(Ljava/util/List;)Ljava/util/List;\n    move-result-object '+m.group(2)+'\n    return-object '+m.group(2),getter.group(0))
        if not n:raise ValueError('Feed getter contains no object returns')
        feedpath.write_text(text[:getter.start()]+body+text[getter.end():],encoding='utf8')
        plans[lookup[FEED]]['add_feed_hook']=True
        changes.append({'family':family,'class':FEED,'method':'getItems()Ljava/util/List;','change':'Filter native ad-marked posts on every return; preserve getter metadata and branches','returns':n})

        if family!='original':
            for c,sigs in [('Lme/tiktokupdatez/f/a;',['a(Landroid/content/Context;)V','d(Landroid/content/Context;)V']),('Lme/tiktokupdatez/f/e;',['run()V']),('Lme/tiktokupdatez/f/h;',['run()V'])]:
                p=source_class_path(pathlib.Path(plans[lookup[c]]['patch_dir']),c);text=p.read_text(encoding='utf8')
                was_native=any(re.search(r'\.method[^\n]* native '+re.escape(sig)+r'\n',text) for sig in sigs)
                for sig in sigs:
                    text=replace_method(text,sig,'    .locals 0\n    return-void')
                    changes.append({'family':family,'class':c,'method':sig,'change':'Disable promotional banner display or network fetch'})
                if was_native:
                    if ' native ' in text:raise ValueError('Native class has other methods; cannot omit registration')
                    text=replace_method(text,'<clinit>()V','    .locals 0\n    return-void')
                    changes.append({'family':family,'class':c,'method':'<clinit>()V','change':'Omit native registration for replaced single-method banner worker'})
                p.write_text(text,encoding='utf8')
            if family=='central':
                c='Lcom/tiktok/plugin/client/ClientSettings$CommentWithSticker;'
                p=source_class_path(pathlib.Path(plans[lookup[c]]['patch_dir']),c);text=p.read_text(encoding='utf8')
                text=replace_method(text,'getDefaultValue()Z','    .locals 1\n    const/4 v0, 0x1\n    return v0')
                text=replace_method(text,'<clinit>()V','    .locals 0\n    return-void')
                p.write_text(text,encoding='utf8')
                changes.append({'family':family,'class':c,'method':'getDefaultValue()Z','change':'Enable existing comment-sticker client gate without native settings dependency'})
        else:
            p=source_class_path(pathlib.Path(plans[lookup[STICKER]]['patch_dir']),STICKER);text=p.read_text(encoding='utf8')
            # Keep IMStickerApi eligibility checks. Override only the experiment bit.
            field='iget v0, v0, Lcom/ss/android/ugc/aweme/experiment/CommentWithStickerExp$CommentStickerConfig;->stickerClickEnable:I'
            if text.count(field)!=1:raise ValueError('Unexpected sticker click gate')
            text=text.replace(field,'const/4 v0, 0x1')
            text=replace_method(text,'LIZIZ()Z','    .locals 1\n    const/4 v0, 0x1\n    return v0')
            p.write_text(text,encoding='utf8')
            changes.append({'family':family,'class':STICKER,'method':'LIZ()/LIZIZ()','change':'Enable sticker experiment click/send bits while retaining IM eligibility check'})
            if region:
                values={'getSimCountryIso':'by','getNetworkCountryIso':'by','getSimOperator':'25702','getNetworkOperator':'25702','getSimOperatorName':'MTS','getNetworkOperatorName':'MTS'}
                count=0
                pattern=r'(?m)^(?P<indent>\s*)invoke-virtual(?:/range)? \{[^}]+\}, Landroid/telephony/TelephonyManager;->(?P<name>get(?:Sim|Network)(?:CountryIso|OperatorName|Operator))\(\)Ljava/lang/String;(?P<between>\n(?:(?!\s*move-result-object)[^\n]*\n)*?)\s*move-result-object (?P<register>[vp]\d+)'
                for plan in plans.values():
                    for p in pathlib.Path(plan['patch_dir']).rglob('*.smali'):
                        text=p.read_text(encoding='utf8')
                        def sub(m):
                            # Between invoke and move-result only labels and debug directives are legal here.
                            for line in m.group('between').splitlines():
                                line=line.strip()
                                if line and not line.startswith(('.',':','#')):raise ValueError('Unexpected instruction between invoke and result')
                            return m.group('indent')+'nop'+m.group('between')+'    const-string '+m.group('register')+', "'+values[m.group('name')]+'"'
                        text,n=re.subn(pattern,sub,text)
                        if n:
                            p.write_text(text,encoding='utf8');count+=n
                            changes.append({'family':family,'class':str(p.relative_to(pathlib.Path(plan['patch_dir']))),'change':'Use Belarus SIM country/operator values as in Central default','calls':n})
                if count!=11:raise ValueError('Expected 11 SIM string calls, got '+str(count))
    (ROOT/'analysis/build-plan.json').write_text(json.dumps({'region':region,'families':all_plans,'changes':changes},ensure_ascii=False,indent=2),encoding='utf8')
    print('Prepared reviewable patches:',len(changes),flush=True)

def signing_key():
    d=ROOT/'tools/signing';d.mkdir(parents=True,exist_ok=True)
    key=d/'local-clean.jks';pw=d/'password.txt'
    if not key.exists():
        if pw.exists():raise FileExistsError('Password exists without keystore; inspect before retry')
        pw.write_text(secrets.token_urlsafe(32),encoding='ascii')
        run([JAVA.with_name('keytool.exe'),'-genkeypair','-keystore',key,'-alias','local-clean','-keyalg','RSA','-keysize','3072','-validity','10000','-storepass:file',pw,'-keypass:file',pw,'-dname','CN=Local TikTok Clean, OU=Personal build, O=Local'])
    return key,pw

def build(only=None):
    plan=json.loads((ROOT/'analysis/build-plan.json').read_text(encoding='utf8'))
    modified={}
    for family,entries in plan['families'].items():
        if only and family!=only:continue
        modified[family]={}
        for name,entry in entries.items():
            d=ROOT/'analysis/built-dex'/family;d.mkdir(parents=True,exist_ok=True)
            patch=d/(name+'.patch');out=d/name
            dex('assemble',entry['patch_dir'],patch)
            merges=[entry['input'],str(patch)]
            if entry.get('add_feed_hook'):merges.append(str(ROOT/'analysis/hook-dex/classes.dex'))
            dex('merge',*merges,out)
            modified[family][name]=out
    key,pw=signing_key();results=[]
    inputs=[('original',FAMILIES['original'])]+[(family,n) for family,n in FAMILIES.items() if family!='original']
    inputs.extend([('platinum','TikTok_Platinum_v47.1.7_(MOD)_arm7.apk'),('private','TikTok_Private_Plus_v47.1.7_(MOD)_arm7.apk')])
    for family,name in inputs:
        if only and family!=only:continue
        source=verify_source(name)
        output_name='TikTok_Clean_47.1.4_Universal.apk' if family=='original' else source.stem.replace('_(MOD)','_Clean')+'.apk'
        out=ROOT/'output'/output_name
        unsigned=ROOT/'analysis'/(output_name+'.unsigned')
        aligned=ROOT/'analysis'/(output_name+'.aligned')
        with zipfile.ZipFile(source) as src,zipfile.ZipFile(unsigned,'w',allowZip64=True) as dst:
            names=src.namelist()
            if len(names)!=len(set(names)):raise ValueError('Duplicate ZIP entries')
            for info in src.infolist():
                # Preserve service files in META-INF; remove only old APK signing artifacts.
                if info.filename=='stamp-cert-sha256' or re.fullmatch(r'META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))',info.filename,re.I):continue
                if family=='original' and info.filename=='AndroidManifest.xml':
                    data=(ROOT/'analysis/clean-manifest.axml').read_bytes()
                elif info.filename in modified[family]:
                    expected=json.loads((ROOT/'analysis'/path_for(FAMILIES[family]).stem/'inventory.json').read_text(encoding='utf8'))
                    expected_hash=next(e['sha256'] for e in expected['entries'] if e['name']==info.filename)
                    if hashlib.sha256(src.read(info)).hexdigest()!=expected_hash:raise ValueError('ARM pair DEX differs: '+info.filename)
                    data=modified[family][info.filename].read_bytes()
                else:data=src.read(info)
                dst.writestr(info,data)
            if family=='original' and plan.get('original_extra_dex'):
                max_number=max(int(re.search(r'classes(\d*)\.dex',n).group(1) or '1') for n in names if re.fullmatch(r'classes\d*\.dex',n))
                dst.writestr('classes'+str(max_number+1)+'.dex',pathlib.Path(plan['original_extra_dex']).read_bytes(),compress_type=zipfile.ZIP_DEFLATED)
                dst.writestr('assets/clean-update-channel.json',(ROOT/'assets/clean-update-channel.json').read_bytes(),compress_type=zipfile.ZIP_DEFLATED)
        run([BT/'zipalign.exe','-f','-P','16','4',unsigned,aligned])
        run([JAVA,'-jar',BT/'lib/apksigner.jar','sign','--ks',key,'--ks-key-alias','local-clean','--ks-pass','file:'+str(pw),'--v1-signing-enabled','true','--v2-signing-enabled','true','--v3-signing-enabled','true','--v4-signing-enabled','false','--out',out,aligned])
        run([JAVA,'-jar',BT/'lib/apksigner.jar','verify','--verbose','--print-certs',out])
        run([BT/'zipalign.exe','-c','-P','16','4',out])
        changed=set(modified[family]);preserved=0
        if family=='original':changed.add('AndroidManifest.xml')
        with zipfile.ZipFile(source) as src,zipfile.ZipFile(out) as dst:
            for info in src.infolist():
                n=info.filename
                if n in changed or n=='stamp-cert-sha256' or re.fullmatch(r'META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))',n,re.I):continue
                if hashlib.sha256(src.read(n)).digest()!=hashlib.sha256(dst.read(n)).digest():raise ValueError('Unexpected changed entry: '+n)
                preserved+=1
            if dst.testzip() is not None:raise ValueError('Output ZIP CRC failure')
        results.append({'file':str(out),'sha256':sha(out),'size':out.stat().st_size,'input_sha256':EXPECTED[name],'modified_dex':sorted(changed),'preserved_entries':preserved,'signature_verified':True,'zip_16k_alignment_verified':True})
        print('VERIFIED',output_name,out.stat().st_size,flush=True)
    prior=ROOT/'analysis/build-results.json'
    if only and prior.exists():
        replaced={r['file'] for r in results}
        results.extend(r for r in json.loads(prior.read_text(encoding='utf8')) if r['file'] not in replaced)
    prior.write_text(json.dumps(results,indent=2),encoding='utf8')
    print('All outputs verified:',len(results),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','build']);parser.add_argument('--region',choices=['belarus','original'],default='belarus');parser.add_argument('--family',choices=list(FAMILIES));args=parser.parse_args()
    if args.stage=='prepare':prepare(args.region=='belarus')
    else:build(args.family)
