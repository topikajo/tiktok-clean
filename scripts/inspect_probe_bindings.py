import pathlib,re
p=pathlib.Path('analysis/bridge-smali/classes6/X/0BVS.smali').read_text(encoding='utf8')
for name in ['setSender','setMsgId','setConversationId','setCreatedAt','setContent','isSuccessStatus']:
 print(name,re.findall(r'(?m)^\.method[^\n]* '+name+r'[^\n]*',p))
