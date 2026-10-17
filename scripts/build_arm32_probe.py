"""Signed offline verifier fixtures for the separately installed ARM32 profile."""
import json,pathlib,re,subprocess,time,zipfile
from build_clean import ROOT,JAVA,BT
android=BT.parent.parent/'platforms/android-36.1/android.jar'
out=ROOT/'analysis'/('arm32-probe-'+str(time.time_ns()));out.mkdir()
for part in ['classes','dex','assets']:(out/part).mkdir()
def run(args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
legacy=(ROOT/'tests/android/ProbeInstrumentation.java').read_text(encoding='utf8').replace('package mod.clean.probe;','package mod.arm32.probe;').replace('class ProbeInstrumentation','class Arm32LegacyProbeInstrumentation')
legacy=legacy.replace('private boolean begun;','private boolean begun,appReady,configReady;').replace('if(begun)return;begun=true;','if(begun||!appReady||!configReady)return;begun=true;')
legacy=legacy.replace('invoke(null,app);}catch','invoke(null,app);cls("mod.arm32.Runtime32").getMethod("install",Application.class).invoke(null,app);}catch')
legacy=legacy.replace('throw new RuntimeException(e);}begin();','throw new RuntimeException(e);}appReady=true;begin();').replace('super.onCreate(args);begin();','super.onCreate(args);configReady=true;begin();')
legacy=legacy.replace('Class<?> updates=cls("mod.clean.UpdateChannel")','Class<?> updates=cls("mod.arm32.UpdateChannel")')
legacy=legacy.replace('PackageManager.GET_SIGNING_CERTIFICATES','(android.os.Build.VERSION.SDK_INT>=28?PackageManager.GET_SIGNING_CERTIFICATES:PackageManager.GET_SIGNATURES)')
legacy=legacy.replace('installed.getLongVersionCode()==2024701041L','(android.os.Build.VERSION.SDK_INT>=28?installed.getLongVersionCode():installed.versionCode)==2024701042L')
source=out/'Arm32LegacyProbeInstrumentation.java';source.write_text(legacy,encoding='utf8',newline='\n')
run([JAVA.with_name('javac.exe'),'--release','8','-encoding','UTF-8','-cp',android,'-d',out/'classes',ROOT/'tests/android/Arm32ProbeInstrumentation.java',source])
run([JAVA.with_name('jar.exe'),'cf',out/'probe.jar','-C',out/'classes','.'])
run([JAVA,'-cp',BT/'lib/d8.jar','com.android.tools.r8.D8','--lib',android,'--min-api','23','--output',out/'dex',out/'probe.jar'])
version=int(re.search(r'^VERSION=(\d+)',(ROOT/'scripts/build_arm32_clean.py').read_text(encoding='utf8'),re.M)[1])
key=ROOT/'tools/signing/local-clean.jks';password='file:'+str(ROOT/'tools/signing/password.txt')
wrong=out/'fixture-key.jks';run([JAVA.with_name('keytool.exe'),'-genkeypair','-keystore',wrong,'-storepass','fixture-only','-keypass','fixture-only','-alias','fixture','-dname','CN=Disposable test fixture','-keyalg','RSA','-validity','2'])
with zipfile.ZipFile(ROOT/'originals/TikTok_47.1.4_original_apkpure.apk') as source:
    def small_lib(abi):
        candidates=sorted((n for n in source.namelist() if n.startswith('lib/'+abi+'/') and n.endswith('.so')),key=lambda n:source.getinfo(n).file_size)
        return next((n,source.read(n)) for n in candidates if source.read(n).startswith(b'\x7fELF'))
    arm32=small_lib('armeabi-v7a');arm64=small_lib('arm64-v8a')
for name,pkg,v,bad in [('future','com.zhiliaoapp.musically',version+1,False),('same-version','com.zhiliaoapp.musically',version,False),('wrong-package','mod.arm32.wrongfixture',version+1,False),('wrong-signer','com.zhiliaoapp.musically',version+1,True),('wrong-abi','com.zhiliaoapp.musically',version+1,False)]:
    manifest=out/(name+'.xml');manifest.write_text(f'<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="{pkg}" android:versionCode="{v}"><uses-sdk android:minSdkVersion="23" android:targetSdkVersion="30"/><application android:hasCode="false"/></manifest>',encoding='utf8')
    apk=out/(name+'-unsigned.apk');run([BT/'aapt2.exe','link','-I',android,'--manifest',manifest,'-o',apk])
    with zipfile.ZipFile(apk,'a') as dest:dest.writestr(*(arm64 if name=='wrong-abi' else arm32))
    run([JAVA,'-jar',BT/'lib/apksigner.jar','sign','--ks',wrong if bad else key,'--ks-pass','pass:fixture-only' if bad else password,'--out',out/'assets'/(name+'.apk'),apk])
run([BT/'aapt2.exe','link','-I',android,'--manifest',ROOT/'tests/android/Arm32ProbeManifest.xml','-A',out/'assets','-o',out/'unsigned.apk'])
with zipfile.ZipFile(out/'unsigned.apk','a') as dest:dest.write(out/'dex/classes.dex','classes.dex')
run([BT/'zipalign.exe','-f','4',out/'unsigned.apk',out/'aligned.apk'])
run([JAVA,'-jar',BT/'lib/apksigner.jar','sign','--ks',key,'--ks-pass',password,'--out',out/'probe.apk',out/'aligned.apk'])
(ROOT/'analysis/arm32-probe-path.txt').write_text(str(out/'probe.apk'),encoding='utf8')
print(out/'probe.apk',flush=True)
