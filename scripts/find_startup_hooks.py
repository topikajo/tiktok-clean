import pathlib
for family in ['central','platinum','private']:
 p=pathlib.Path('analysis',family+'-calls.tsv');lines=p.read_text(encoding='utf8').splitlines()
 print(family,'root')
 for l in lines:
  parts=l.split('\t')
  if len(parts)==5 and parts[-1].startswith('Lme/tiktokupdatez/a;->a('):print(l)
