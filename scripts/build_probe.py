import pathlib,subprocess,os,zipfile
root=pathlib.Path(__file__).resolve().parents[1]
sdk=pathlib.Path(os.environ['LOCALAPPDATA'])/'Android/Sdk';bt=sdk/'build-tools/36.1.0';java=pathlib.Path(os.environ['JAVA_HOME'])/'bin/java.exe';android=sdk/'platforms/android-36.1/android.jar'
out=root/'analysis/android-probe';out.mkdir(parents=True,exist_ok=True);(out/'classes').mkdir(exist_ok=True);(out/'dex').mkdir(exist_ok=True)
def run(args):subprocess.run([str(a) for a in args],cwd=root,check=True)
run([java.with_name('javac.exe'),'--release','8','-encoding','UTF-8','-cp',android,'-d',out/'classes',root/'tests/android/ProbeInstrumentation.java'])
run([java.with_name('jar.exe'),'cf',out/'probe.jar','-C',out/'classes','.'])
run([java,'-cp',bt/'lib/d8.jar','com.android.tools.r8.D8','--lib',android,'--min-api','23','--output',out/'dex',out/'probe.jar'])
run([bt/'aapt2.exe','link','-I',android,'--manifest',root/'tests/android/AndroidManifest.xml','-o',out/'unsigned.apk'])
with zipfile.ZipFile(out/'unsigned.apk','a') as z:z.write(out/'dex/classes.dex','classes.dex')
run([bt/'zipalign.exe','-f','4',out/'unsigned.apk',out/'aligned.apk'])
run([java,'-jar',bt/'lib/apksigner.jar','sign','--ks',root/'tools/signing/local-clean.jks','--ks-pass','file:'+str(root/'tools/signing/password.txt'),'--out',out/'probe.apk',out/'aligned.apk'])
print(out/'probe.apk')
