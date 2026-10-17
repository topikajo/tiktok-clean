"""Decode constant StringFog AES calls for review, without executing APK code."""
import base64, hashlib, json, pathlib, re
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
ROOT = pathlib.Path(__file__).resolve().parents[1]
records=[]
for path in (ROOT/'analysis/you-bundled-smali').rglob('*.smali'):
    regs={};method=''
    for line in path.read_text(encoding='utf8').splitlines():
        if line.startswith('.method'):
            method=line;regs={}
        m=re.search(r'const-string(?:/jumbo)? ([vp]\d+), (".*")',line)
        if m:
            try:regs[m[1]]=json.loads(m[2])
            except ValueError:regs.pop(m[1],None)
        if 'StringFogRuntime;->decrypt' not in line:continue
        m=re.search(r'\{([^}]+)\}',line)
        args=[regs.get(r.strip()) for r in m[1].split(',')]
        if len(args)!=3 or None in args or args[2]!='aes':continue
        try:
            raw=base64.b64decode(args[0]);key=hashlib.sha256(args[1].encode()).digest()[:16]
            d=Cipher(algorithms.AES(key),modes.CBC(raw[:16])).decryptor()
            value=d.update(raw[16:])+d.finalize();value=value[:-value[-1]].decode('utf8')
            records.append({'class':str(path.relative_to(ROOT/'analysis/you-bundled-smali')),'method':method,'value':value,'encrypted':args[0],'key':args[1]})
        except (ValueError,UnicodeError):pass
out=ROOT/'analysis/you-decoded-strings.json'
out.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
print('Decoded calls',len(records))
for r in records:
    if re.search(r'https?://|analytics|telemetry|statistic|track|update|crash|permission|广告|advert',r['value'],re.I):
        print(r['class'],r['method'],r['value'].replace('\n','\\n'))
