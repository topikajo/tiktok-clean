import pathlib,sys,zipfile,io
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/native-python'))
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
from elftools.elf.elffile import ELFFile
b=zipfile.ZipFile(ROOT/'others/TikTok_You-4.4-(46.8.3).apk').read('lib/arm64-v8a/libttmod.so')
e=ELFFile(io.BytesIO(b));md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
address=int(sys.argv[1],0) if len(sys.argv)>1 else 0x242f8
length=int(sys.argv[2],0) if len(sys.argv)>2 else 1244
for s in e.iter_segments():
 if s['p_type']=='PT_LOAD' and s['p_vaddr']<=address<s['p_vaddr']+s['p_filesz']:
  off=address-s['p_vaddr']+s['p_offset'];break
for i in md.disasm(b[off:off+length],address):print(f'{i.address:08x} {i.mnemonic:8} {i.op_str}')
