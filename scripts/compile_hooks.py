"""Compile production helpers separately from JVM test stubs, then run focused tests."""
import pathlib,os,subprocess,time
root=pathlib.Path(__file__).resolve().parents[1]
java=pathlib.Path(os.environ['JAVA_HOME'])/'bin/java.exe'
sdk=pathlib.Path(os.environ['LOCALAPPDATA'])/'Android/Sdk'
android=sdk/'platforms/android-36.1/android.jar'
stub=root/'analysis/compile-stubs';out=root/'analysis'/('clean-classes-'+str(time.time_ns()));test=root/'analysis/unit-tests';dex=root/'analysis/clean-dex'
for p in (stub,out,test,dex):p.mkdir(parents=True,exist_ok=True)
def run(args):subprocess.run([str(a) for a in args],cwd=root,check=True)
run([java.with_name('javac.exe'),'--release','8','-encoding','UTF-8','-d',stub,root/'tests/stubs/com/ss/android/ugc/aweme/feed/model/Aweme.java'])
run([java.with_name('javac.exe'),'--release','8','-encoding','UTF-8','-cp',str(android)+os.pathsep+str(stub),'-d',out,*sorted((root/'src/mod/clean').glob('*.java'))])
run([java.with_name('jar.exe'),'cf',root/'analysis/clean-hooks.jar','-C',out,'mod'])
run([java,'-cp',sdk/'build-tools/36.1.0/lib/d8.jar','com.android.tools.r8.D8','--lib',android,'--min-api','23','--output',dex,root/'analysis/clean-hooks.jar'])
run([java.with_name('javac.exe'),'--release','8','-encoding','UTF-8','-cp',os.pathsep.join(map(str,[android,out,stub])),'-d',test,root/'tests/FeedAdsTest.java',root/'tests/PolicyTest.java',root/'tests/UpdateTransportTest.java',root/'tests/AuthRoutingTest.java'])
for name in ('FeedAdsTest','PolicyTest','mod.clean.UpdateTransportTest','AuthRoutingTest'):run([java,'-cp',os.pathsep.join(map(str,[test,out,stub,android])),name])
legacy=root/'analysis/hook-dex';legacy.mkdir(parents=True,exist_ok=True)
run([java.with_name('jar.exe'),'cf',root/'analysis/hook.jar','-C',out,'mod/clean/FeedAds.class'])
run([java,'-cp',sdk/'build-tools/36.1.0/lib/d8.jar','com.android.tools.r8.D8','--lib',android,'--min-api','21','--output',legacy,root/'analysis/hook.jar'])
print('Production DEX contains only mod.clean classes; test doubles compiled separately.')
