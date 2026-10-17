import pathlib,re,collections
p=pathlib.Path('analysis/TikTok_47.1.4_original_apkpure/classes.tsv')
patterns={'chat-ui':r'(?:ChatRoomActivity|ChatRoomFragment|Setting.*Activity|Settings.*Activity|AwemeHostApplication);','messages':r'(?:/IMClient;|/IIMClient;|/TextContent;|/Message;|SendMessage|RecallMessage|EditMessage|ModifyMessage)','streak':r'(?:/.*Streak.*Service|/.*Streak.*Api|/.*Streak.*Manager|/.*Streak.*Restore)'}
ls=p.read_text(encoding='utf8').splitlines()
for k,pat in patterns.items():
 hits=[l for l in ls if re.search(pat,l)];pathlib.Path('analysis',k+'-classes.tsv').write_text('\n'.join(hits),encoding='utf8');print(k,'count',len(hits));print('\n'.join(hits[:45]))
