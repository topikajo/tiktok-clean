"""Hash-pinned privacy fork of the user-supplied You 4.4 APK. No old 47.x patches are used."""
import collections,hashlib,json,os,pathlib,re,subprocess,time,zipfile
from audit_apks import Dex
from build_clean import ROOT,JAVA,BT,CP,dex,replace_method,source_class_path,signing_key,sha
from you_manifest import patch as manifest_patch

SOURCE=ROOT/'others/TikTok_You-4.4-(46.8.3).apk'
EXPECTED='c9da98aa3cfd25806cd08a456ca39bc2ffb4b8d3efb129de7cf2c49795fedb17'
VERSION=2024608034
BUNDLE='assets/tty/bundled/classes.dex'
OUT=ROOT/'output/TikTok_Clean_46.8.3_You_Privacy_ARM64.apk'
WORK=ROOT/'analysis/you-build'
SELECT={
 'Lcom/ss/android/ugc/aweme/app/host/AwemeHostApplication;',
 'Lcom/bytedance/applog/AppLog;','Lcom/ss/android/common/applog/AppLog;',
 'LX/03RH;','Lcom/appsflyer/internal/AFb1vSDK;',
 'Lcom/google/android/gms/ads/identifier/AdvertisingIdClient;',
 'Lcom/bytedance/applog/priority/PriorityWrapper;',
 'Lcom/bytedance/retrofit2/client/Request;','Lokhttp3/Request;',
 'Lcom/ttnet/org/chromium/net/impl/CronetUrlRequest;',
 'Lcom/google/firebase/analytics/FirebaseAnalytics;','La/g;',
 'LX/07ss;','Lcom/ss/android/ugc/aweme/feed/adapter/VideoViewCell;',
 'Lcom/ss/android/ugc/aweme/common/widget/VerticalViewPager;',
 'Lcom/ss/android/ugc/aweme/inbox/InboxShellFragment;',
 'Lcom/ss/android/ugc/aweme/notification/sysnotice/SystemNotificationContainerFragment;',
 'Lcom/windukk/stable/DynamicUpdates;',
 'Lcom/windukk/mod/Main;','LZ/pb;','LZ/p;','LZ/ua;','LZ/le;','LZ/m6;','LZ/l1;','LZ/rg;',
}
changes=[]
def run(args):
 subprocess.run(list(map(str,args)),cwd=ROOT,check=True,timeout=600)
def signatures(text):
 return re.findall(r'^\.method [^\n]*? ([^ \n]+\([^\n]*)$',text,re.M)
def no_op(text,sig,descriptor,reason,body=None):
 if body is None:body='    .locals 0\n    return-void'
 changes.append({'class':descriptor,'method':sig,'change':reason})
 return replace_method(text,sig,body)
def edit(desc,fn):
 p=source_class_path(dirs[lookup[desc]],desc);original=p.read_text(encoding='utf8')
 value=fn(original)
 if value==original:raise ValueError('Empty patch: '+desc)
 p.write_text(value,encoding='utf8')
def all_void(desc,name_re,reason):
 def apply(text):
  count=0
  for sig in signatures(text):
   if sig.endswith(')V') and re.fullmatch(name_re,sig.split('(')[0]):text=no_op(text,sig,desc,reason);count+=1
  if count==0:raise ValueError('No matching methods: '+desc)
  return text
 edit(desc,apply)

if sha(SOURCE)!=EXPECTED:raise ValueError('Source changed; audit the new APK before building')
WORK.mkdir(parents=True,exist_ok=True)
patch_root=ROOT/'patches/you-privacy'/str(time.time_ns())
if patch_root.exists():raise FileExistsError('Use a fresh patch directory or review existing patches first')
# Refresh call-site inventory from the pinned APK; do not depend on a cached audit.
calls=ROOT/'analysis/you-permission-calls.tsv'
dex('references',SOURCE,calls,r'Landroid(?:x)?/(?:app|fragment/app)/[^;]*;->requestPermissions')
lookup={};classes_before={}
with zipfile.ZipFile(SOURCE) as z:
 for name in z.namelist():
  if re.fullmatch(r'classes\d*\.dex',name) or name==BUNDLE:
   cs=Dex(z.read(name)).classes;classes_before[name]=set(cs)
   for c in cs:lookup[c]=name
 # Identify every direct framework permission request, including the inherited mod payload.
 for line in calls.read_text(encoding='utf8').splitlines():
  parts=line.split('\t')
  if len(parts)==3 and re.match(r'Landroid(?:x)?/(?:app|fragment/app)/[^;]*;->requestPermissions',parts[2]):SELECT.add(parts[1].split('->')[0])
 groups=collections.defaultdict(list)
 for desc in sorted(SELECT):groups[lookup[desc]].append(desc)
 dirs={}
 for name,classes in groups.items():
  original=WORK/'input'/name;original.parent.mkdir(parents=True,exist_ok=True);original.write_bytes(z.read(name))
  directory=patch_root/name.replace('/','_').replace('.dex','');dirs[name]=directory
  dex('disassemble',original,directory,*classes)

for desc in ['Lcom/bytedance/applog/AppLog;','Lcom/ss/android/common/applog/AppLog;']:
 all_void(desc,r'.*onEvent.*|onActivity.*|onResume|onPause|recordMiscLog|flush(?:Async)?|activeUser|addAppCount',
          'Discard analytics events before queueing; preserve initialization/device registration')
edit('LX/03RH;',lambda t:no_op(t,'LLLILZ(LX/04PL;)V','LX/03RH;','Discard events at the concrete AppLog receiver before observers, cache and database'))
all_void('Lcom/bytedance/applog/priority/PriorityWrapper;',r'LIZJ|LIZLLL|LJ|LJI', 'Disable native priority analytics sessions, start and flush')
edit('Lcom/bytedance/applog/priority/PriorityWrapper;',lambda t:
 no_op(no_op(t,'LJFF(I)Z','Lcom/bytedance/applog/priority/PriorityWrapper;','No priority analytics event eligibility','    .locals 1\n    const/4 v0, 0x0\n    return v0'),
       'LJII(ILjava/lang/String;LX/0897;)Z','Lcom/bytedance/applog/priority/PriorityWrapper;','Do not collect or forward native priority events','    .locals 1\n    const/4 v0, 0x0\n    return v0'))
all_void('Lcom/appsflyer/internal/AFb1vSDK;',r'start|logEvent|setCustomerUserId|setUserEmails|sendAdRevenue|sendPushNotificationData|updateServerUninstallToken', 'Disable AppsFlyer attribution and event reporting')
edit('Lcom/appsflyer/internal/AFb1vSDK;',lambda t:
 no_op(no_op(t,'init(Ljava/lang/String;Lcom/appsflyer/AppsFlyerConversionListener;Landroid/content/Context;)Lcom/appsflyer/AppsFlyerLib;',
             'Lcom/appsflyer/internal/AFb1vSDK;','Do not initialize attribution SDK','    .locals 0\n    return-object p0'),
       'getAppsFlyerUID(Landroid/content/Context;)Ljava/lang/String;','Lcom/appsflyer/internal/AFb1vSDK;','No AppsFlyer installation identifier','    .locals 1\n    const-string v0, ""\n    return-object v0'))
edit('Lcom/google/android/gms/ads/identifier/AdvertisingIdClient;',lambda t:
 no_op(t,'getAdvertisingIdInfo(Landroid/content/Context;)Lcom/google/android/gms/ads/identifier/AdvertisingIdClient$Info;',
 'Lcom/google/android/gms/ads/identifier/AdvertisingIdClient;','Do not connect to advertising ID service; return blank ID with limit-tracking=true',
 '    .locals 3\n    new-instance v0, Lcom/google/android/gms/ads/identifier/AdvertisingIdClient$Info;\n    const-string v1, ""\n    const/4 v2, 0x1\n    invoke-direct {v0, v1, v2}, Lcom/google/android/gms/ads/identifier/AdvertisingIdClient$Info;-><init>(Ljava/lang/String;Z)V\n    return-object v0'))
all_void('Lcom/google/firebase/analytics/FirebaseAnalytics;',r'setCurrentScreen','Disable Firebase automatic screen reporting; permanent analytics deactivation in manifest')

def guard_string_fields(t,desc,field):
 pattern=r'(?m)^(\s*)iput-object ([vp]\d+), p0, '+re.escape(desc+'->'+field+':Ljava/lang/String;')+'$'
 def sub(m):
  reg=m[2];return f'    invoke-static/range {{{reg} .. {reg}}}, Lmod/privacy/PrivacyNet;->rewrite(Ljava/lang/String;)Ljava/lang/String;\n    move-result-object {reg}\n'+m[0]
 t,n=re.subn(pattern,sub,t)
 if not n:raise ValueError('No URL fields: '+desc)
 changes.append({'class':desc,'change':'Apply narrow telemetry URL denylist before transport stores URL','sites':n})
 return t
edit('Lcom/bytedance/retrofit2/client/Request;',lambda t:guard_string_fields(t,'Lcom/bytedance/retrofit2/client/Request;','url'))
edit('Lcom/ttnet/org/chromium/net/impl/CronetUrlRequest;',lambda t:guard_string_fields(t,'Lcom/ttnet/org/chromium/net/impl/CronetUrlRequest;','LJIIJ'))
def okhttp(t):
 marker='    iput-object v0, p0, Lokhttp3/Request;->url:LX/04x1;'
 if t.count(marker)!=1:raise ValueError('Unexpected OkHttp URL constructor')
 guard='''    if-eqz v0, :clean_url_ok
    invoke-virtual {v0}, LX/04x1;->toString()Ljava/lang/String;
    move-result-object v1
    invoke-static {v1}, Lmod/privacy/PrivacyNet;->blocked(Ljava/lang/String;)Z
    move-result v1
    if-eqz v1, :clean_url_ok
    const-string v1, "https://127.0.0.1:9/clean-privacy-blocked"
    invoke-static {v1}, LX/04x1;->LJIIIZ(Ljava/lang/String;)LX/04x1;
    move-result-object v0
    :clean_url_ok
'''
 changes.append({'class':'Lokhttp3/Request;','change':'Apply denylist to the actual parsed OkHttp destination'})
 return t.replace(marker,guard+marker)
edit('Lokhttp3/Request;',okhttp)

# Every original permission request identified in the audit goes through the local foreground/action gate.
permission_sites=0
for name,directory in dirs.items():
 for path in directory.rglob('*.smali'):
  text=path.read_text(encoding='utf8')
  def request(m):
   global permission_sites
   permission_sites+=1
   typ=m['type'];method='request' if typ=='Landroid/app/Activity;' else 'requestFragment' if typ=='Landroid/app/Fragment;' else 'requestSupport'
   arg='Ljava/lang/Object;' if method=='requestSupport' else typ
   op='invoke-static/range' if '/range' in m['op'] else 'invoke-static'
   return op+' '+m['args']+', Lmod/privacy/PrivacyRuntime;->'+method+'('+arg+'[Ljava/lang/String;I)V'
  text,n=re.subn(r'(?P<op>invoke-virtual(?:/range)?) (?P<args>\{[^}]+\}), (?P<type>Landroid/app/Activity;|Landroid/app/Fragment;|Landroidx/fragment/app/Fragment;)->requestPermissions\(\[Ljava/lang/String;I\)V',request,text)
  if n:path.write_text(text,encoding='utf8');changes.append({'class':str(path.relative_to(directory)),'change':'Require foreground user action; preserve real grant/denial callbacks','sites':n})
if permission_sites!=4:raise ValueError('Unexpected framework permission sites: '+str(permission_sites))
def app_entry(t):
 sig='onCreate()V';m=re.search(r'^\.method[^\n]* '+re.escape(sig)+r'\n.*?^\.end method',t,re.M|re.S)
 body,n=re.subn(r'(\.registers \d+\n)',r'\1\n    invoke-static {p0}, Lmod/privacy/PrivacyRuntime;->install(Landroid/app/Application;)V\n',m[0],count=1)
 if n!=1:raise ValueError('Cannot install lifecycle hooks')
 changes.append({'class':'Lcom/ss/android/ugc/aweme/app/host/AwemeHostApplication;','method':sig,'change':'Install permission UX without jobs, telemetry or account collection'})
 return t[:m.start()]+body+t[m.end():]
edit('Lcom/ss/android/ugc/aweme/app/host/AwemeHostApplication;',app_entry)

def hook_method(t,desc,sig,entry='',before_return=''):
 m=re.search(r'^\.method[^\n]* '+re.escape(sig)+r'\n.*?^\.end method',t,re.M|re.S)
 if not m:raise ValueError('Missing native hook point: '+desc+'->'+sig)
 body=m[0]
 if entry:
  body,n=re.subn(r'(\.registers \d+\n)',lambda m:m[0]+'\n'+entry+'\n',body,count=1)
  if n!=1:raise ValueError('No register header')
 if before_return:
  body,n=re.subn(r'(?m)^    return-void$',before_return+'\n    return-void',body)
  if n<1:raise ValueError('No native method returns')
 changes.append({'class':desc,'method':sig,'change':'Local current-video retention / clean frame export hooks; native behavior is preserved'})
 return t[:m.start()]+body+t[m.end():]
edit('LX/07ss;',lambda t:hook_method(t,'LX/07ss;','LJJI(Lcom/ss/android/ugc/aweme/feed/model/FeedItemList;)V',
 entry='    invoke-static/range {p0 .. p0}, Lmod/privacy/NativeRefresh;->begin(Ljava/lang/Object;)V',
 before_return='    invoke-static/range {p0 .. p0}, Lmod/privacy/NativeRefresh;->finish(Ljava/lang/Object;)V'))
def player_hooks(t):
 desc='Lcom/ss/android/ugc/aweme/feed/adapter/VideoViewCell;'
 for sig,method in [('LJIILIIL(I)V','selected'),('onPageSelected(I)V','selected'),
   ('onRenderFirstFrame(LX/09Wp;)V','firstFrame')]:
  t=hook_method(t,desc,sig,before_return='    invoke-static/range {p0 .. p0}, Lmod/privacy/NativeRefresh;->'+method+'(Ljava/lang/Object;)V')
 t=hook_method(t,desc,'onPlayProgressChange(F)V',entry='    invoke-static/range {p0 .. p1}, Lmod/privacy/NativeRefresh;->progress(Ljava/lang/Object;F)V')
 for sig,method in [('onPausePlay(Ljava/lang/String;)V','paused'),('onResumePlay(Ljava/lang/String;)V','resumed')]:
  t=hook_method(t,desc,sig,before_return='    invoke-static/range {p0 .. p0}, Lmod/privacy/FrameActions;->'+method+'(Ljava/lang/Object;)V')
 return t
edit('Lcom/ss/android/ugc/aweme/feed/adapter/VideoViewCell;',player_hooks)
edit('Lcom/ss/android/ugc/aweme/common/widget/VerticalViewPager;',lambda t:hook_method(t,
 'Lcom/ss/android/ugc/aweme/common/widget/VerticalViewPager;','LJJIL(IZZI)V',
 entry='    invoke-static/range {p0 .. p1}, Lmod/privacy/NativeRefresh;->initialIndex(Ljava/lang/Object;I)I\n    move-result p1'))

for inbox in ['Lcom/ss/android/ugc/aweme/inbox/InboxShellFragment;',
              'Lcom/ss/android/ugc/aweme/notification/sysnotice/SystemNotificationContainerFragment;']:
 def inbox_hooks(t):
  t=hook_method(t,inbox,'onViewCreated(Landroid/view/View;Landroid/os/Bundle;)V',before_return='    invoke-static/range {p0 .. p0}, Lmod/privacy/UpdateChannel;->attachInbox(Ljava/lang/Object;)V')
  if inbox.endswith('/InboxShellFragment;'):
   t=hook_method(t,inbox,'onResume()V',before_return='    invoke-static/range {p0 .. p0}, Lmod/privacy/UpdateChannel;->attachInbox(Ljava/lang/Object;)V')
  return t
 edit(inbox,inbox_hooks)

# Pin the dynamically loaded mod to its packaged code, including installations that already have a downloaded slot.
edit('La/g;',lambda t:no_op(t,'m()La/e;','La/g;','Load only the bundled, hash-checked payload; ignore foreign downloaded slots',
 '    .locals 1\n    invoke-virtual {p0}, La/g;->d()La/e;\n    move-result-object v0\n    return-object v0'))
edit('Lcom/windukk/stable/DynamicUpdates;',lambda t:no_op(t,'importPackage(Landroid/content/Context;Ljava/io/File;)V','Lcom/windukk/stable/DynamicUpdates;','Disable importing foreign dynamic executable code',
 '    .locals 2\n    new-instance v0, Ljava/io/IOException;\n    const-string v1, "TikTok Clean uses signed APK updates only"\n    invoke-direct {v0, v1}, Ljava/io/IOException;-><init>(Ljava/lang/String;)V\n    throw v0'))
edit('LZ/pb;',lambda t:
 no_op(no_op(t,'a(Z)LZ/ob;','LZ/pb;','No third-party update/statistics request','    .locals 1\n    sget-object v0, LZ/ob;->a:LZ/ob;\n    return-object v0'),
       'a(Landroid/content/Context;)Ljava/util/Map;','LZ/pb;','No Android ID or X-SSAID header','    .locals 1\n    invoke-static {}, Ljava/util/Collections;->emptyMap()Ljava/util/Map;\n    move-result-object v0\n    return-object v0'))
edit('LZ/pb;',lambda t:no_op(t,'a(ZLZ/nb;)V','LZ/pb;','No startup executor work; deliver up-to-date state to explicit UI callback',
 '    .locals 1\n    if-eqz p1, :clean_done\n    sget-object v0, LZ/ob;->a:LZ/ob;\n    invoke-interface {p1, v0}, LZ/nb;->a(LZ/ob;)V\n    :clean_done\n    return-void'))
def prefs(t):
 # Use a disposable local at the end of construction; do not overwrite reused default-value registers.
 sig='<init>(Landroid/content/SharedPreferences;)V'
 m=re.search(r'^\.method[^\n]* '+re.escape(sig)+r'\n.*?^\.end method',t,re.M|re.S)
 clamp='    const/4 v0, 0x0\n    iput-boolean v0, p0, LZ/ua;->z:Z\n    iput-boolean v0, p0, LZ/ua;->A:Z\n    iget-object v1, p0, LZ/ua;->a:Landroid/content/SharedPreferences;\n    const-string v2, "auto_streak_nudge_enabled"\n    invoke-interface {v1, v2, v0}, Landroid/content/SharedPreferences;->getBoolean(Ljava/lang/String;Z)Z\n    move-result v0\n    iput-boolean v0, p0, LZ/ua;->o:Z\n    const/4 v0, 0x1\n    iput-boolean v0, p0, LZ/ua;->B:Z\n    iput-boolean v0, p0, LZ/ua;->d:Z\n'
 if m[0].count('    return-void')!=1:raise ValueError('Unexpected settings constructor returns')
 body=m[0].replace('    return-void',clamp+'    return-void')
 t=t[:m.start()]+body+t[m.end():]
 # Each setter's boolean parameter is isolated to that setting.
 for sig,val in [('n(Z)V',0),('f(Z)V',0),('h(Z)V',1)]:
  m=re.search(r'^\.method[^\n]* '+re.escape(sig)+r'\n.*?^\.end method',t,re.M|re.S)
  body,n=re.subn(r'(\.registers \d+\n)',r'\1\n    const/4 p1, 0x'+str(val)+'\n',m[0],count=1)
  if n!=1:raise ValueError('Unexpected settings setter')
  t=t[:m.start()]+body+t[m.end():]
 changes.append({'class':'LZ/ua;','change':'Permanently disable third-party statistics/OTA; retain ad hiding, skip obsolete consent dialog and default automatic chat nudges to off'})
 return t
edit('LZ/ua;',prefs)
edit('LZ/le;',lambda t:no_op(t,'n()Landroid/widget/LinearLayout;','LZ/le;','Replace obsolete statistics/OTA toggles with honest privacy controls',
 '    .locals 1\n    invoke-static {p0}, Lmod/privacy/PrivacyRuntime;->settingsView(Landroid/app/Activity;)Landroid/widget/LinearLayout;\n    move-result-object v0\n    return-object v0'))
edit('LZ/m6;',lambda t:t.replace('"TikTok You"','"TikTok Clean"'))
edit('LZ/l1;',lambda t:no_op(no_op(t,'b(Landroid/content/Context;)V','LZ/l1;','Disable background supporter price fetch'),
 'f()V','LZ/l1;','Disable startup supporter badge fetch; bundled fallback is retained'))
def mod_transport(t):
 sig='b(Ljava/lang/String;Ljava/lang/String;ILjava/util/Map;Ljava/lang/String;)LZ/o;'
 m=re.search(r'^\.method[^\n]* '+re.escape(sig)+r'\n.*?^\.end method',t,re.M|re.S)
 body,n=re.subn(r'(\.registers \d+\n)',r'\1\n    invoke-static/range {p0 .. p0}, Lmod/privacy/PrivacyNet;->rewrite(Ljava/lang/String;)Ljava/lang/String;\n    move-result-object p0\n',m[0],count=1)
 if n!=1:raise ValueError('Unexpected mod HTTP transport')
 changes.append({'class':'LZ/p;','method':sig,'change':'Guard additional foreign mod API calls without blocking TikTok media CDN requests'})
 return t[:m.start()]+body+t[m.end():]
edit('LZ/p;',mod_transport)
edit('Lcom/windukk/mod/Main;',lambda t:no_op(t,'a(Landroid/content/Context;)V','Lcom/windukk/mod/Main;','Remove original mod signer rejection while keeping native feature initialization'))
# Native declarations, Context and JNI_OnLoad stay as supplied.
all_void('LZ/rg;',r'a|b','Disable original mod full-screen update advertisements')

# Compile this fork's helpers; tests are never packaged.
classes=WORK/('classes-'+str(time.time_ns()));classes.mkdir()
android=BT.parent.parent/'platforms/android-36.1/android.jar'
helper_sources=[p for p in sorted((ROOT/'src/mod/privacy').glob('*.java')) if p.name!='SourceContext.java']
helper_hashes={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in helper_sources}
run([JAVA.with_name('javac.exe'),'--release','8','-encoding','UTF-8','-cp',android,'-d',classes,*helper_sources])
jar=WORK/'privacy.jar';run([JAVA.with_name('jar.exe'),'cf',jar,'-C',classes,'mod'])
helper=WORK/'helper';helper.mkdir(exist_ok=True)
run([JAVA,'-cp',BT/'lib/d8.jar','com.android.tools.r8.D8','--lib',android,'--min-api','23','--output',helper,jar])
modified={}
for name,directory in dirs.items():
 target=WORK/'dex'/name;target.parent.mkdir(parents=True,exist_ok=True);patch=target.with_suffix('.patch.dex')
 dex('assemble',directory,patch);dex('merge',WORK/'input'/name,patch,target);modified[name]=target.read_bytes()
with zipfile.ZipFile(SOURCE) as z:
 from you_native import patch as native_patch
 lib_name='lib/arm64-v8a/libttmod.so'
 modified[lib_name],native_edits=native_patch(z.read(lib_name))
 changes.extend(dict(entry=lib_name,**item) for item in native_edits)
 manifest,removed=manifest_patch(z.read('AndroidManifest.xml'),VERSION);modified['AndroidManifest.xml']=manifest
 meta=json.loads(z.read('assets/tty/bundled/manifest.json'));bhash=hashlib.sha256(modified[BUNDLE]).hexdigest();bsize=len(modified[BUNDLE])
 meta['targetDexSha256']=bhash;meta['targetSize']=bsize;meta['dexFiles'][0]['targetSha256']=bhash;meta['dexFiles'][0]['targetSize']=bsize;meta['hashes']['classes.dex']=bhash
 modified['assets/tty/bundled/manifest.json']=json.dumps(meta,separators=(',',':')).encode()
 unsigned=WORK/'unsigned.apk';aligned=WORK/'aligned.apk'
 extra='classes'+str(max(int(re.fullmatch(r'classes(\d*)\.dex',n)[1] or '1') for n in z.namelist() if re.fullmatch(r'classes\d*\.dex',n))+1)+'.dex'
 signature=re.compile(r'META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))',re.I)
 with zipfile.ZipFile(unsigned,'w',allowZip64=True) as dest:
  for info in z.infolist():
   if info.filename=='stamp-cert-sha256' or signature.fullmatch(info.filename):continue
   dest.writestr(info,modified.get(info.filename,z.read(info)))
  dest.writestr(extra,(helper/'classes.dex').read_bytes(),compress_type=zipfile.ZIP_DEFLATED)
  dest.writestr('assets/clean-update-channel.json',(ROOT/'assets/clean-update-channel.json').read_bytes(),compress_type=zipfile.ZIP_DEFLATED)
key,pw=signing_key();OUT.parent.mkdir(exist_ok=True)
run([BT/'zipalign.exe','-f','-P','16','4',unsigned,aligned])
run([JAVA,'-jar',BT/'lib/apksigner.jar','sign','--ks',key,'--ks-key-alias','local-clean','--ks-pass','file:'+str(pw),'--v1-signing-enabled','true','--v2-signing-enabled','true','--v3-signing-enabled','true','--v4-signing-enabled','false','--out',OUT,aligned])
with (WORK/'signature.txt').open('w') as log:subprocess.run([str(JAVA),'-jar',str(BT/'lib/apksigner.jar'),'verify','--verbose','--print-certs',str(OUT)],stdout=log,stderr=subprocess.STDOUT,check=True)
run([BT/'zipalign.exe','-c','-P','16','4',OUT])
preserved=0
with zipfile.ZipFile(SOURCE) as a,zipfile.ZipFile(OUT) as b:
 if b.testzip():raise ValueError('CRC failure')
 for info in a.infolist():
  if info.filename in modified or info.filename=='stamp-cert-sha256' or signature.fullmatch(info.filename):continue
  if hashlib.sha256(a.read(info)).digest()!=hashlib.sha256(b.read(info.filename)).digest():raise ValueError('Unexpected change '+info.filename)
  preserved+=1
 types=set();output_counts=collections.Counter()
 base_counts=collections.Counter(c for name,cs in classes_before.items() if name!=BUNDLE for c in cs)
 for name in b.namelist():
  if re.fullmatch(r'classes\d*\.dex',name):
   cs=set(Dex(b.read(name)).classes)
   if name==extra and types & cs:raise ValueError('Helper class collision '+str(types & cs))
   output_counts.update(cs)
   types.update(cs)
   if name in classes_before and cs!=classes_before[name]:raise ValueError('Changed class set '+name)
 if set(Dex(b.read(BUNDLE)).classes)!=classes_before[BUNDLE]:raise ValueError('Bundled class set changed')
 if any('Test' in c or 'Probe' in c or 'Fake' in c for c in Dex(b.read(extra)).classes):raise ValueError('Test code leaked')
 for c,count in base_counts.items():
  if output_counts[c]!=count:raise ValueError('Changed class multiplicity '+c)
report={'file':str(OUT),'source':str(SOURCE),'input_sha256':EXPECTED,'sha256':sha(OUT),'size':OUT.stat().st_size,'versionCode':VERSION,
 'baseVersion':'46.8.3','abis':['arm64-v8a'],'changes':changes,'removed_permissions':removed,'permission_request_sites':permission_sites,
 'modified_entries':sorted(modified),'extra_dex':extra,'preserved_entries':preserved,'signature_verified':True,'zip_16k_alignment_verified':True,
 'patch_directory':str(patch_root),
 'class_sets_preserved':True,'native_libraries_unchanged':False,'native_patch_bytes':sum(len(bytes.fromhex(item['after'])) for item in native_edits),'full_app_runtime_verified':False,'account_login_verified':False}
report['inherited_duplicate_classes']={c:n for c,n in base_counts.items() if n>1}
report['helper_source_sha256']=helper_hashes
report['build_inputs_sha256']={p:sha(ROOT/p) for p in ['scripts/build_you_privacy.py','scripts/you_manifest.py','scripts/you_native.py','assets/clean-update-channel.json']}
(ROOT/'release/you-privacy-build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:report[k] for k in ['file','sha256','size','versionCode','preserved_entries','permission_request_sites']},indent=2),flush=True)
