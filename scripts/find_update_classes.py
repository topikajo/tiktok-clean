import pathlib,re
for name in ['TikTok_Private_Plus_v47.1.7_(MOD)_arm8','TikTok_Platinum_v47.1.7_(MOD)_arm8','TikTok_Central_v47.1.7_(MOD)']:
 lines=pathlib.Path('analysis',name,'classes.tsv').read_text(encoding='utf8').splitlines()
 hits=[l for l in lines if re.search(r'(?i)(?:mhmd|aaaaaaa|īi|tiktokupdatez).*(?:update|pk;|ismail;)',l)]
 print(name,hits[:40])
