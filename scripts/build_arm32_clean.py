"""Separate ARMv7 profile from the pinned legacy Clean 47.1.4 build; no You native code."""
import collections,hashlib,json,pathlib,re,subprocess,time,zipfile
from audit_apks import Dex
from build_clean import ROOT,JAVA,BT,dex,source_class_path,replace_method,signing_key,sha
from you_manifest import patch as manifest_patch

SOURCE=ROOT/'output/TikTok_Clean_47.1.4_Universal.apk'
EXPECTED='0baef3eea84a1c0cc32e806a73d59aeaaeb937b842e6ebaacf089cbe102ebdef'
UPSTREAM=ROOT/'originals/TikTok_47.1.4_original_apkpure.apk'
UPSTREAM_SHA='4226ed5d3031b68208c29f62d80ac421b281fc74201bc4163d98e442d0991a40'
VERSION=2024701042
WORK=ROOT/'analysis/arm32-build';PATCH=ROOT/'patches/arm32'/str(time.time_ns())
OUT=ROOT/'output/TikTok_Clean_47.1.4_ARM32.apk'
assert sha(SOURCE)==EXPECTED and sha(UPSTREAM)==UPSTREAM_SHA,'ARM32 base changed; audit before building'
WORK.mkdir(parents=True,exist_ok=True)
def run(args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True,timeout=600)
changes=[];lookup={};base_counts=collections.Counter()
with zipfile.ZipFile(SOURCE) as z:
 for name in z.namelist():
  if re.fullmatch(r'classes\d*\.dex',name):
   classes=set(Dex(z.read(name)).classes);base_counts.update(classes)
   for c in classes:lookup[c]=name
SELECT={'Lcom/ss/android/ugc/aweme/app/host/AwemeHostApplication;',
 'Lcom/bytedance/applog/AppLog;','Lcom/ss/android/common/applog/AppLog;',
 'Lcom/bytedance/applog/priority/PriorityWrapper;','Lcom/appsflyer/internal/AFb1vSDK;',
 'Lcom/google/android/gms/ads/identifier/AdvertisingIdClient;',
 'Lcom/bytedance/retrofit2/client/Request;','Lcom/ttnet/org/chromium/net/impl/CronetUrlRequest;',
 'Lcom/ss/android/ugc/aweme/inbox/InboxShellFragment;',
 'Lcom/ss/android/ugc/aweme/notification/sysnotice/SystemNotificationContainerFragment;'}
calls=WORK/'permission-calls.tsv'
dex('references',SOURCE,calls,r'Landroid(?:x)?/(?:app|fragment/app)/[^;]*;->requestPermissions')
for line in calls.read_text(encoding='utf8').splitlines():
 parts=line.split('\t')
 if len(parts)==3 and '->requestPermissions' in parts[2]:SELECT.add(parts[1].split('->')[0])
groups=collections.defaultdict(list)
for c in SELECT:groups[lookup[c]].append(c)
dirs={}
with zipfile.ZipFile(SOURCE) as z:
 for name,classes in groups.items():
  p=WORK/'input'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
  directory=PATCH/name[:-4];dex('disassemble',p,directory,*sorted(classes));dirs[name]=directory
def edit(c,fn):
 path=source_class_path(dirs[lookup[c]],c);before=path.read_text(encoding='utf8');after=fn(before)
 assert after!=before,'Empty ARM32 patch: '+c
 path.write_text(after,encoding='utf8',newline='\n')
def noop(text,c,pattern,reason):
 count=0
 for sig in re.findall(r'^\.method[^\n]* ([^ \n]+\([^\n]*)$',text,re.M):
  if sig.endswith(')V') and re.fullmatch(pattern,sig.split('(')[0]):text=replace_method(text,sig,'    .locals 0\n    return-void');count+=1
 assert count,'No matching analytics methods: '+c
 changes.append({'class':c,'change':reason,'methods':count});return text
for c in ['Lcom/bytedance/applog/AppLog;','Lcom/ss/android/common/applog/AppLog;']:
 edit(c,lambda t,c=c:noop(t,c,r'.*onEvent.*|onActivity.*|onResume|onPause|recordMiscLog|flush(?:Async)?|activeUser|addAppCount','Discard Java analytics events before queueing'))
c='Lcom/bytedance/applog/priority/PriorityWrapper;'
edit(c,lambda t:noop(t,c,r'LIZJ|LIZLLL|LJ|LJI','Disable priority event sessions and flush'))
c='Lcom/appsflyer/internal/AFb1vSDK;'
def attribution(t):
 t=noop(t,c,r'start|logEvent|setCustomerUserId|setUserEmails|sendAdRevenue|sendPushNotificationData|updateServerUninstallToken','Disable attribution/events')
 t=replace_method(t,'init(Ljava/lang/String;Lcom/appsflyer/AppsFlyerConversionListener;Landroid/content/Context;)Lcom/appsflyer/AppsFlyerLib;','    .locals 0\n    return-object p0')
 return replace_method(t,'getAppsFlyerUID(Landroid/content/Context;)Ljava/lang/String;','    .locals 1\n    const-string v0, ""\n    return-object v0')
edit(c,attribution)
c='Lcom/google/android/gms/ads/identifier/AdvertisingIdClient;'
edit(c,lambda t:replace_method(t,'getAdvertisingIdInfo(Landroid/content/Context;)Lcom/google/android/gms/ads/identifier/AdvertisingIdClient$Info;',
 '    .locals 3\n    new-instance v0, Lcom/google/android/gms/ads/identifier/AdvertisingIdClient$Info;\n    const-string v1, ""\n    const/4 v2, 0x1\n    invoke-direct {v0, v1, v2}, Lcom/google/android/gms/ads/identifier/AdvertisingIdClient$Info;-><init>(Ljava/lang/String;Z)V\n    return-object v0'))
for c in ['Lcom/bytedance/retrofit2/client/Request;','Lcom/ttnet/org/chromium/net/impl/CronetUrlRequest;']:
 def strings(t):
  def guard(m):
   reg=m[1];return '    invoke-static/range {'+reg+' .. '+reg+'}, Lmod/arm32/PrivacyNet;->rewrite(Ljava/lang/String;)Ljava/lang/String;\n    move-result-object '+reg+'\n'+m[0]
  t,n=re.subn(r'(?m)^\s*iput-object ([vp]\d+), p0, '+re.escape(c)+r'->[^:]+:Ljava/lang/String;$',guard,t)
  assert n,'No transport string assignments: '+c
  changes.append({'class':c,'change':'Apply narrow analytics URL denylist to string fields','sites':n});return t
 edit(c,strings)
permission_sites=0
for directory in dirs.values():
 for path in directory.rglob('*.smali'):
  t=path.read_text(encoding='utf8')
  def permissions(m):
   global permission_sites
   permission_sites+=1;receiver=m[3]
   method='requestSupport' if 'androidx/fragment' in receiver else 'requestFragment' if receiver!='Landroid/app/Activity;' else 'request'
   typ='Ljava/lang/Object;' if method=='requestSupport' else receiver
   return 'invoke-static'+(m[1] or '')+' '+m[2]+', Lmod/arm32/Runtime32;->'+method+'('+typ+'[Ljava/lang/String;I)V'
  t,n=re.subn(r'invoke-virtual(/range)? (\{[^}]+\}), (Landroid/app/Activity;|Landroid/app/Fragment;|Landroidx/fragment/app/Fragment;)->requestPermissions\(\[Ljava/lang/String;I\)V',permissions,t)
  if n:path.write_text(t,encoding='utf8',newline='\n')
assert permission_sites>0,'No framework permission hooks'
def hook(t,c,sig,code,entry=False):
 m=re.search(r'^\.method[^\n]* '+re.escape(sig)+r'\n.*?^\.end method',t,re.M|re.S);assert m,'Missing ARM32 hook '+sig
 body=m[0]
 if entry:body,n=re.subn(r'(\.registers \d+\n)',lambda m:m[0]+code+'\n',body,count=1)
 else:body,n=re.subn(r'(?m)^    return-void$',code+'\n    return-void',body)
 assert n,'No ARM32 hook returns';return t[:m.start()]+body+t[m.end():]
c='Lcom/ss/android/ugc/aweme/app/host/AwemeHostApplication;'
edit(c,lambda t:hook(t,c,'onCreate()V','    invoke-static/range {p0 .. p0}, Lmod/arm32/Runtime32;->install(Landroid/app/Application;)V',True))
for c in ['Lcom/ss/android/ugc/aweme/inbox/InboxShellFragment;','Lcom/ss/android/ugc/aweme/notification/sysnotice/SystemNotificationContainerFragment;']:
 def inbox(t):
  t=hook(t,c,'onViewCreated(Landroid/view/View;Landroid/os/Bundle;)V','    invoke-static/range {p0 .. p0}, Lmod/arm32/UpdateChannel;->attachInbox(Ljava/lang/Object;)V')
  if c.endswith('/InboxShellFragment;'):t=hook(t,c,'onResume()V','    invoke-static/range {p0 .. p0}, Lmod/arm32/UpdateChannel;->attachInbox(Ljava/lang/Object;)V')
  return t
 edit(c,inbox)

generated=WORK/'generated';(generated/'mod/arm32').mkdir(parents=True,exist_ok=True);(generated/'mod/clean').mkdir(parents=True,exist_ok=True)
for name in ['CachedReflect','PermissionPolicy','PrivacyNet','UpdatePolicy','UpdateChannel']:
 text=(ROOT/'src/mod/privacy'/f'{name}.java').read_text(encoding='utf8').replace('package mod.privacy;','package mod.arm32;').replace('PrivacyRuntime.','Runtime32.')
 if name=='UpdateChannel':
  text=text.replace('2131381843','2131382041') # Pinned original 47.1.4 BottomTabAssemBase.rq().
  marker='        PackageManager pm=context.getPackageManager();'
  assert marker in text
  text=text.replace(marker,'        try(java.util.zip.ZipFile archive=new java.util.zip.ZipFile(file)){boolean arm32=false;java.util.Enumeration<? extends java.util.zip.ZipEntry> entries=archive.entries();while(entries.hasMoreElements()){String name=entries.nextElement().getName();if(name.startsWith("lib/armeabi-v7a/"))arm32=true;else if(name.startsWith("lib/")&&!entriesDirectory(name))throw new SecurityException("Wrong ABI");}if(!arm32)throw new SecurityException("Missing ARM32 libraries");}\n'+marker)
  text=text.replace('    private static void download(', '    private static boolean entriesDirectory(String name){return name.endsWith("/");}\n    private static void download(',1)
 (generated/'mod/arm32'/f'{name}.java').write_text(text,encoding='utf8',newline='\n')
(generated/'mod/arm32/Runtime32.java').write_bytes((ROOT/'src/mod/arm32/Runtime32.java').read_bytes())
for source in (ROOT/'src/mod/clean').glob('*.java'):
 if source.name=='UpdateChannel.java':continue
 text=source.read_text(encoding='utf8')
 if source.name=='NativeBridge.java':
  start=text.index('    public static Object call(');end=text.index('    public static String uid()',start)
  text=text[:start]+'    public static Object call(Object object,String name,Object...args)throws Exception{return mod.arm32.CachedReflect.call(object,name,args);}\n'+text[end:]
 if source.name=='CleanApp.java':
  start=text.index('        try{\n            JobScheduler scheduler=')
  end=text.index('        }catch(Exception ignored){}',start)+len('        }catch(Exception ignored){}')
  text=text[:start]+'        updateStreakSchedule();'+text[end:]
  marker='    public static SharedPreferences prefs()'
  scheduling='''    private static boolean hasEnabledStreaks(){for(Map.Entry<String,?> e:prefs().getAll().entrySet())if(e.getKey().startsWith("auto|")&&Boolean.TRUE.equals(e.getValue()))return true;return false;}
    private static void updateStreakSchedule(){try{JobScheduler scheduler=(JobScheduler)context.getSystemService(Context.JOB_SCHEDULER_SERVICE);if(!hasEnabledStreaks()){scheduler.cancel(47141);return;}JobInfo info=new JobInfo.Builder(47141,new ComponentName(context,StreakJob.class)).setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY).setPeriodic(30*60*1000L).build();scheduler.schedule(info);}catch(Exception ignored){}}
'''
  text=text.replace(marker,scheduling+marker,1)
  text=text.replace('StreakJob.tick();','if(hasEnabledStreaks())StreakJob.tick();')
  text=text.replace('auto.setText(!enabled?', 'updateStreakSchedule();auto.setText(!enabled?',1)
 (generated/'mod/clean'/source.name).write_text(text,encoding='utf8',newline='\n')
(generated/'mod/clean/UpdateChannel.java').write_text('package mod.clean; public final class UpdateChannel { public static void attach(android.app.Activity a){mod.arm32.UpdateChannel.attach(a);} }\n',encoding='utf8')
android=BT.parent.parent/'platforms/android-36.1/android.jar';classes=WORK/('classes-'+str(time.time_ns()));classes.mkdir()
run([JAVA.with_name('javac.exe'),'--release','8','-encoding','UTF-8','-cp',android,'-d',classes,*sorted(generated.rglob('*.java')),ROOT/'tests/stubs/com/ss/android/ugc/aweme/feed/model/Aweme.java'])
jar=WORK/'helpers.jar';run([JAVA.with_name('jar.exe'),'cf',jar,'-C',classes,'mod'])
helper=WORK/'helper';helper.mkdir(exist_ok=True)
run([JAVA,'-cp',BT/'lib/d8.jar','com.android.tools.r8.D8','--lib',android,'--min-api','23','--output',helper,jar])
modified={}
for name,directory in dirs.items():
 p=WORK/'dex'/name;p.parent.mkdir(parents=True,exist_ok=True);patch=p.with_suffix('.patch.dex')
 dex('assemble',directory,patch);dex('merge',WORK/'input'/name,patch,p);modified[name]=p.read_bytes()
with zipfile.ZipFile(SOURCE) as z:
 helper_types=set(Dex((helper/'classes.dex').read_bytes()).classes)
 # Merge replacements into the existing helper DEX, preserving unrelated original classes.
 old_name=lookup['Lmod/clean/CleanApp;'];base=WORK/'legacy-helpers.dex';base.write_bytes(modified.get(old_name,z.read(old_name)))
 merged=WORK/'merged-helpers.dex';dex('merge',base,helper/'classes.dex',merged);modified[old_name]=merged.read_bytes()
 manifest,removed=manifest_patch(z.read('AndroidManifest.xml'),VERSION);modified['AndroidManifest.xml']=manifest
 modified['assets/clean-update-channel.json']=(ROOT/'assets/clean-update-channel-arm32.json').read_bytes()
 unsigned=WORK/'unsigned.apk';aligned=WORK/'aligned.apk';signature=re.compile(r'META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))',re.I)
 omitted=[]
 with zipfile.ZipFile(unsigned,'w',allowZip64=True) as dest:
  for item in z.infolist():
   if item.filename.startswith('lib/') and not item.filename.startswith('lib/armeabi-v7a/'):omitted.append(item.filename);continue
   if item.filename=='stamp-cert-sha256' or signature.fullmatch(item.filename):continue
   dest.writestr(item,modified.get(item.filename,z.read(item)))
key,pw=signing_key();run([BT/'zipalign.exe','-f','-P','16','4',unsigned,aligned])
run([JAVA,'-jar',BT/'lib/apksigner.jar','sign','--ks',key,'--ks-key-alias','local-clean','--ks-pass','file:'+str(pw),'--v1-signing-enabled','true','--v2-signing-enabled','true','--v3-signing-enabled','true','--v4-signing-enabled','false','--out',OUT,aligned])
with (WORK/'signature.txt').open('w') as log:subprocess.run(list(map(str,[JAVA,'-jar',BT/'lib/apksigner.jar','verify','--verbose','--print-certs',OUT])),check=True,stdout=log,stderr=subprocess.STDOUT)
run([BT/'zipalign.exe','-c','-P','16','4',OUT])
with zipfile.ZipFile(SOURCE) as a,zipfile.ZipFile(UPSTREAM) as upstream,zipfile.ZipFile(OUT) as b:
 assert b.testzip() is None
 libs=[n for n in b.namelist() if n.startswith('lib/') and n.endswith('.so')];assert libs and all(n.startswith('lib/armeabi-v7a/') for n in libs)
 elf_count=0
 for n in libs:
  data=b.read(n);assert data==a.read(n)==upstream.read(n),'Native ARM32 library differs from original: '+n
  if data.startswith(b'\x7fELF'):
   assert data[4]==1 and int.from_bytes(data[18:20],'little')==40,'Not ELF32 ARM: '+n
   elf_count+=1
 for info in a.infolist():
  if info.filename in modified or info.filename in omitted or info.filename=='stamp-cert-sha256' or signature.fullmatch(info.filename):continue
  assert a.read(info)==b.read(info.filename),'Unexpected ARM32 change: '+info.filename
 counts=collections.Counter()
 for name in b.namelist():
  if re.fullmatch(r'classes\d*\.dex',name):counts.update(set(Dex(b.read(name)).classes))
 assert not any(n>1 for n in counts.values()),'Duplicate ARM32 classes'
 assert all(counts[c]==count for c,count in base_counts.items()),'Original class set changed'
 assert all(counts[c]==1 for c in helper_types),'ARM32 helper missing'
 assert not any('Test' in c or 'Probe' in c or 'Fake' in c for c in helper_types),'Test code leaked'
report={'file':str(OUT),'sha256':sha(OUT),'size':OUT.stat().st_size,'versionCode':VERSION,'baseVersion':'47.1.4','profile':'original-47-arm32',
 'source':str(SOURCE),'source_sha256':EXPECTED,'upstream':str(UPSTREAM),'upstream_sha256':UPSTREAM_SHA,'abis':['armeabi-v7a'],
 'native_libraries':len(libs),'elf32_arm_libraries':elf_count,'native_libraries_byte_identical_to_official':True,'omitted_foreign_abi_entries':len(omitted),'permission_request_sites':permission_sites,
 'removed_permissions':removed,'changes':changes,'modified_entries':sorted(modified),'signature_verified':True,'zip_16k_alignment_verified':True,
 'source_sha256s':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in [ROOT/'scripts/build_arm32_clean.py',ROOT/'src/mod/arm32/Runtime32.java',ROOT/'assets/clean-update-channel-arm32.json',*sorted((ROOT/'src/mod/clean').glob('*.java')),*[ROOT/'src/mod/privacy'/f'{n}.java' for n in ['CachedReflect','PermissionPolicy','PrivacyNet','UpdatePolicy','UpdateChannel']]]},
 'normal_startup_verified':False,'physical_device_verified':False,'account_login_verified':False,'feature_limits':['No You-specific native features','Feed retention and clean-frame export not ported to ARM32','Real Google/email login and chat features need device/account validation']}
(ROOT/'release/arm32-build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:report[k] for k in ['file','sha256','size','versionCode','abis','native_libraries']},indent=2),flush=True)
