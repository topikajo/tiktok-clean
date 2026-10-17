"""Inventory all APK entries and index every DEX class/string without executing APKs."""
import hashlib
import json
import pathlib
import re
import struct
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis'

def u32(data, off):
    return struct.unpack_from('<I', data, off)[0]

def uleb(data, off):
    result = shift = 0
    while True:
        b = data[off]
        off += 1
        result |= (b & 127) << shift
        if not b & 128:
            return result, off
        shift += 7

class Dex:
    def __init__(self, data):
        if data[:4] != b'dex\n':
            raise ValueError('Unsupported DEX magic')
        self.data = data
        self.strings = []
        for i in range(u32(data, 56)):
            off = u32(data, u32(data, 60) + i * 4)
            _, off = uleb(data, off)
            end = data.index(0, off)
            self.strings.append(data[off:end].decode('utf-8', errors='replace'))
        self.types = [self.strings[u32(data, u32(data, 68) + i * 4)] for i in range(u32(data, 64))]
        self.classes = [self.types[u32(data, u32(data, 100) + i * 32)] for i in range(u32(data, 96))]

def sha_file(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def audit(path):
    dest = OUT / path.stem
    dest.mkdir(parents=True, exist_ok=True)
    entries = []
    dex_list = []
    urls = set()
    interesting = re.compile(r'comment.*(sticker|gif|image|photo|voice|poll)|(?:sticker|gif).*(?:comment)|centraltiktok|platinum|private.?plus|modcloud|tiktok.?mod|tiktok.?plugin|https?://|платин|реклам|подпиш|канал', re.I)
    with zipfile.ZipFile(path) as z, (dest/'classes.tsv').open('w',encoding='utf-8') as cf, (dest/'interesting-strings.tsv').open('w',encoding='utf-8') as sf:
        for info in z.infolist():
            data = z.read(info)
            sha = hashlib.sha256(data).hexdigest()
            entries.append({'name':info.filename,'size':info.file_size,'compressed':info.compress_size,'sha256':sha,'crc':info.CRC})
            if not re.fullmatch(r'classes(?:\d+)?\.dex',info.filename):
                continue
            cache = OUT/'dex-index'/sha
            if not (cache/'summary.json').exists():
                cache.mkdir(parents=True,exist_ok=True)
                d = Dex(data)
                (cache/'classes.txt').write_text('\n'.join(d.classes)+'\n',encoding='utf-8')
                matched=[s.replace('\n','\\n').replace('\t','\\t') for s in d.strings if interesting.search(s)]
                (cache/'strings.txt').write_text('\n'.join(matched)+'\n',encoding='utf-8')
                (cache/'summary.json').write_text(json.dumps({'classes':len(d.classes),'strings':len(d.strings),'methods':u32(data,88),'types':len(d.types)}),encoding='utf-8')
            summary=json.loads((cache/'summary.json').read_text())
            dex_list.append({'name':info.filename,'sha256':sha,**summary})
            for line in (cache/'classes.txt').read_text(encoding='utf-8').splitlines():
                cf.write(info.filename+'\t'+line+'\n')
            for line in (cache/'strings.txt').read_text(encoding='utf-8').splitlines():
                sf.write(info.filename+'\t'+line+'\n')
                urls.update(re.findall(r'https?://[^\s<>"\\]+',line))
    result={'file':path.name,'sha256':sha_file(path),'size':path.stat().st_size,'entries':entries,'dex':dex_list,'abis':sorted({e['name'].split('/')[1] for e in entries if e['name'].startswith('lib/')})}
    (dest/'inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (dest/'urls.txt').write_text('\n'.join(sorted(urls)),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['file','sha256','size','abis']}),flush=True)
    return result

if __name__ == '__main__':
    import sys
    paths=[pathlib.Path(p) for p in sys.argv[1:]] or sorted((ROOT/'others').glob('*.apk'))
    results=[audit(p) for p in paths]
    (OUT/'summary.json').write_text(json.dumps([{k:r[k] for k in ['file','sha256','size','abis','dex']} for r in results],indent=2),encoding='utf-8')
