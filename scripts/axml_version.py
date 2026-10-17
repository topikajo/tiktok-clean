"""Change only the typed Android versionCode attribute, preserving resources/string indices."""
import struct
from axml_add_service import u32,length8,length16

def set_version_code(data,version):
    data=bytearray(data);off=struct.unpack_from('<H',data,2)[0];strings=[];changed=0
    while off<len(data):
        kind,h,size=struct.unpack_from('<HHI',data,off)
        if kind==1:
            count,styles,flags,start,style_start=struct.unpack_from('<IIIII',data,off+8)
            for i in range(count):
                pos=off+start+u32(data,off+h+4*i)
                if flags&256:_,pos=length8(data,pos);n,pos=length8(data,pos);strings.append(data[pos:pos+n].decode('utf8'))
                else:n,pos=length16(data,pos);strings.append(data[pos:pos+n*2].decode('utf-16-le'))
        elif kind==0x102 and strings[u32(data,off+20)]=='manifest':
            start,stride,count=struct.unpack_from('<HHH',data,off+24)
            for i in range(count):
                pos=off+16+start+i*stride
                if strings[u32(data,pos+4)]=='versionCode':
                    if data[pos+15]!=0x10:raise ValueError('versionCode is not an integer')
                    struct.pack_into('<I',data,pos+16,version);changed+=1
        off+=size
    if off!=len(data) or changed!=1:raise ValueError('Expected exactly one versionCode attribute')
    return bytes(data)
