import pathlib,subprocess,os,zipfile,time,sys
from build_clean import ROOT,JAVA,BT
android=BT.parent.parent/'platforms/android-36.1/android.jar'
stress='--stress' in sys.argv
updates='--updates' in sys.argv
stem='PrivacyUpdate' if updates else 'PrivacyStress' if stress else 'PrivacyProbe'
out=ROOT/'analysis'/(('you-stress-probe-' if stress else 'you-probe-')+str(time.time_ns()));out.mkdir(parents=True)
for n in ['classes','dex']:(out/n).mkdir()
def run(args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
run([JAVA.with_name('javac.exe'),'--release','8','-encoding','UTF-8','-cp',android,'-d',out/'classes',ROOT/('tests/android/'+stem+'Instrumentation.java'),*sorted((ROOT/'tests/android/stubs').rglob('*.java'))])
run([JAVA.with_name('jar.exe'),'cf',out/'probe.jar','-C',out/'classes','.'])
run([JAVA,'-cp',BT/'lib/d8.jar','com.android.tools.r8.D8','--lib',android,'--min-api','23','--output',out/'dex',out/'probe.jar'])
assets=[]
if updates:
 import re
 version=int(re.search(r'^VERSION=(\d+)',(ROOT/'scripts/build_you_privacy.py').read_text(encoding='utf8'),re.M)[1])
 fixtures=out/'assets';fixtures.mkdir()
 wrong=out/'fixture-key.jks'
 run([JAVA.with_name('keytool.exe'),'-genkeypair','-keystore',wrong,'-storepass','fixture-only','-keypass','fixture-only','-alias','fixture','-dname','CN=Disposable test fixture','-keyalg','RSA','-validity','2'])
 for name,pkg,v,bad in [('future','com.zhiliaoapp.musically',version+1,False),('same-version','com.zhiliaoapp.musically',version,False),('wrong-package','mod.privacy.wrongfixture',version+1,False),('wrong-signer','com.zhiliaoapp.musically',version+1,True)]:
  manifest=out/(name+'.xml');manifest.write_text(f'<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="{pkg}" android:versionCode="{v}"><uses-sdk android:minSdkVersion="23"/><application android:hasCode="false"/></manifest>',encoding='utf8')
  run([BT/'aapt2.exe','link','-I',android,'--manifest',manifest,'-o',out/(name+'-unsigned.apk')])
  run([JAVA,'-jar',BT/'lib/apksigner.jar','sign','--ks',wrong if bad else ROOT/'tools/signing/local-clean.jks','--ks-pass','pass:fixture-only' if bad else 'file:'+str(ROOT/'tools/signing/password.txt'),'--out',fixtures/(name+'.apk'),out/(name+'-unsigned.apk')])
 assets=['-A',fixtures]
run([BT/'aapt2.exe','link','-I',android,'--manifest',ROOT/('tests/android/'+stem+'Manifest.xml'),*assets,'-o',out/'unsigned.apk'])
with zipfile.ZipFile(out/'unsigned.apk','a') as z:z.write(out/'dex/classes.dex','classes.dex')
run([BT/'zipalign.exe','-f','4',out/'unsigned.apk',out/'aligned.apk'])
run([JAVA,'-jar',BT/'lib/apksigner.jar','sign','--ks',ROOT/'tools/signing/local-clean.jks','--ks-pass','file:'+str(ROOT/'tools/signing/password.txt'),'--out',out/'probe.apk',out/'aligned.apk'])
(ROOT/('analysis/you-update-probe-path.txt' if updates else 'analysis/you-stress-probe-path.txt' if stress else 'analysis/you-probe-path.txt')).write_text(str(out/'probe.apk'),encoding='utf8')
print(out/'probe.apk')
