"""Compile current production Java; run policy and byte-level updater tests without network."""
import os,pathlib,subprocess
root=pathlib.Path(__file__).resolve().parents[1]
java=pathlib.Path(os.environ['JAVA_HOME'])/'bin/java.exe'
android=pathlib.Path(os.environ['LOCALAPPDATA'])/'Android/Sdk/platforms/android-36.1/android.jar'
out=root/'analysis/jvm-tests';out.mkdir(parents=True,exist_ok=True)
sources=[p for p in (root/'src/mod/privacy').glob('*.java') if p.name!='SourceContext.java']
subprocess.run([str(java.with_name('javac.exe')),'--release','8','-encoding','UTF-8','-cp',str(android),'-d',str(out),*map(str,sources),str(root/'tests/PrivacyPolicyTest.java'),str(root/'tests/PrivacyUpdateTest.java')],check=True)
for cls,file in [('PrivacyPolicyTest','you-policy-results.txt'),('mod.privacy.PrivacyUpdateTest','you-update-results.txt')]:
    result=subprocess.run([str(java),'-Xmx256m','-cp',str(out)+os.pathsep+str(android),cls],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (root/'analysis'/file).write_text(result.stdout,encoding='utf8');print(result.stdout.strip())
