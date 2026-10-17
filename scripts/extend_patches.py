"""Extend the reviewed base patches with chat UI, paired-message hooks and updater removal."""
import json,pathlib,re,zipfile
from build_clean import ROOT,FAMILIES,path_for,dex,source_class_path,replace_method

plan=json.loads((ROOT/'analysis/build-plan.json').read_text(encoding='utf8'))

def add(family,descriptors):
    source=path_for(FAMILIES[family])
    lookup={c:d for d,c in (l.split('\t') for l in (ROOT/'analysis'/source.stem/'classes.tsv').read_text(encoding='utf8').splitlines())}
    grouped={}
    for c in descriptors:
        if c not in lookup:continue
        grouped.setdefault(lookup[c],[]).append(c)
    with zipfile.ZipFile(source) as z:
        for name,classes in grouped.items():
            p=ROOT/'analysis/build-inputs'/family/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
            d=ROOT/'patches'/family/name[:-4];dex('disassemble',p,d,*classes)
            entries=plan['families'][family]
            if name not in entries:entries[name]={'input':str(p),'patch_dir':str(d),'classes':[]}
            entries[name]['classes'].extend(c for c in classes if c not in entries[name]['classes'])
    return {c:source_class_path(ROOT/'patches'/family/lookup[c][:-4],c) for c in descriptors if c in lookup}

def suppress_native_worker(p):
    s=p.read_text(encoding='utf8')
    s=replace_method(s,'run()V','    .locals 0\n    return-void')
    if re.search(r'(?m)^\.method[^\n]* native ',s):raise ValueError('Unexpected additional native methods')
    if '<clinit>()V' in s:s=replace_method(s,'<clinit>()V','    .locals 0\n    return-void')
    p.write_text(s,encoding='utf8')

worker='Līi/ïi/pk$100000008;'
for family in ['central','private']:
    for c,p in add(family,[worker]).items():
        suppress_native_worker(p);plan['changes'].append({'family':family,'class':c,'method':'run()V','change':'Disable AFMod/LiteAPKs forced update network worker'})

gold=['Lcom/aaaaaaa/gold/CheckUpdate;','Lcom/aaaaaaa/tiktokgold/UpdateChecker;']
for c,p in add('central',gold).items():
    s=p.read_text(encoding='utf8')
    signatures=re.findall(r'(?m)^\.method[^\n]* native ([^\n]+)\n',s)
    for sig in signatures:
        result=sig.split(')')[-1]
        if result=='V':body='    .locals 0\n    return-void'
        elif result.startswith(('L','[')):body='    .locals 1\n    const/4 v0, 0x0\n    return-object v0'
        else:raise ValueError('Unexpected updater return: '+sig)
        s=replace_method(s,sig,body)
    s=replace_method(s,'<clinit>()V','    .locals 0\n    return-void');p.write_text(s,encoding='utf8')
    plan['changes'].append({'family':'central','class':c,'change':'Disable all native methods in dedicated mod update component and omit its native registration','methods':len(signatures)})

cs=['Lcom/ss/android/ugc/aweme/app/host/AwemeHostApplication;','Lcom/ss/android/ugc/aweme/im/chatroom/api/model/SessionInfo;','LX/0BVS;']
paths=add('original',cs)
app=paths[cs[0]];s=app.read_text(encoding='utf8')
pat=r'(?m)^\.method[^\n]* onCreate\(\)V\n.*?^\.end method'
m=re.search(pat,s,re.S|re.M)
if not m:raise ValueError('Missing application onCreate')
body,n=re.subn(r'(?m)^\s*return-void\s*$', '    invoke-static/range {p0 .. p0}, Lmod/clean/CleanApp;->install(Landroid/app/Application;)V\n    return-void',m.group(0))
if n<1:raise ValueError('Unexpected application returns')
app.write_text(s[:m.start()]+body+s[m.end():],encoding='utf8')

session=paths[cs[1]];s=session.read_text(encoding='utf8');m=re.search(r'(?m)^\.method[^\n]* getConversationId\(\)Ljava/lang/String;\n.*?^\.end method',s,re.S|re.M)
if not m:raise ValueError('Missing session getter')
body,n=re.subn(r'(?m)^\s*return-object ([vp]\d+)\s*$',lambda m:'    invoke-static {p0, '+m.group(1)+'}, Lmod/clean/CleanApp;->rememberSession(Ljava/lang/Object;Ljava/lang/String;)V\n    return-object '+m.group(1),m.group(0))
if n<1:raise ValueError('Unexpected session returns')
session.write_text(s[:m.start()]+body+s[m.end():],encoding='utf8')

message=paths[cs[2]];s=message.read_text(encoding='utf8')
for signature,hook,result in [('getContent()Ljava/lang/String;','render(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/String;','object'),('isDeleted()Z','deleted(Ljava/lang/Object;Z)Z',''),('getDeleted()I','deletedInt(Ljava/lang/Object;I)I','')]:
    m=re.search(r'(?m)^\.method[^\n]* '+re.escape(signature)+r'\n.*?^\.end method',s,re.S|re.M)
    if not m:raise ValueError(signature)
    op='return-object' if result else 'return'
    move='move-result-object' if result else 'move-result'
    body,n=re.subn(r'(?m)^\s*'+op+r' ([vp]\d+)\s*$',lambda m:'    invoke-static {p0, '+m.group(1)+'}, Lmod/clean/MessageHooks;->'+hook+'\n    '+move+' '+m.group(1)+'\n    '+op+' '+m.group(1),m.group(0))
    if not n:raise ValueError('No message return')
    s=s[:m.start()]+body+s[m.end():]
message.write_text(s,encoding='utf8')
for entries in [plan['families']['original']]:
    for entry in entries.values():
        if entry.get('add_feed_hook'):entry['add_feed_hook']=False
plan['original_extra_dex']=str(ROOT/'analysis/clean-dex/classes.dex')
plan['changes'].append({'family':'original','change':'Application lifecycle chat/settings UI, account-scoped auto streak JobService, authenticated paired-client display edits/deletes, trusted optional update feed'})
(ROOT/'analysis/build-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
print('Extended patches ready',flush=True)
