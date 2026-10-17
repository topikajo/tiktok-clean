import pathlib,re,json,zipfile
ls=pathlib.Path('analysis/TikTok_47.1.4_original_apkpure/classes.tsv').read_text(encoding='utf8').splitlines()
selected=[l for l in ls if re.search(r'(?:/SessionInfo;|/TextContent;|/AccountService;|/AccountProxyService;|im/.*Chat.*Activity[^/]*;|/IMSendMessageService;|/IIMSendMessageService;|/AwemeHostApplication;|/SettingContainerActivity;|/SendMessageViewModel;|/StreakCompensationApi;|/StreakService;)',l)]
pathlib.Path('analysis/integration-classes.tsv').write_text('\n'.join(selected),encoding='utf8');print('\n'.join(selected))
d=pathlib.Path('analysis/dex/integration');d.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile('originals/TikTok_47.1.4_original_apkpure.apk') as z:
 for dex in set(l.split('\t')[0] for l in selected):(d/dex).write_bytes(z.read(dex))
