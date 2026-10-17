"""Pinned ARM64 rejection branches in the supplied You 4.4 library.

Keep initialization and feature hooks; bypass only error branches which call
the mod's notifier, kill(getpid(), 9), and _exit(0). Input APK is hash-pinned
by the caller. Instructions and branch destinations were disassembled.
"""
import io, struct
from elftools.elf.elffile import ELFFile

def patch(data):
    out = bytearray(data)
    elf = ELFFile(io.BytesIO(data))
    edits = []
    def at(address, expected, replacement, explanation):
        seg = next(s for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD'
                   and s['p_vaddr'] <= address < s['p_vaddr'] + s['p_filesz'])
        offset = address - seg['p_vaddr'] + seg['p_offset']
        before = data[offset:offset + len(expected)]
        if before != expected:
            raise ValueError('Native input differs at ' + hex(address))
        out[offset:offset + len(expected)] = replacement
        edits.append(dict(virtual_address=hex(address), file_offset=offset,
                          before=before.hex(), after=replacement.hex(), change=explanation))
    def branch(source, target):
        return struct.pack('<I', 0x14000000 | (((target-source)//4) & 0x3ffffff))
    # Signature rejection in the initializer: return success via its own epilogue.
    at(0x3b4c8, bytes.fromhex('1f2003d528173b10'),
       bytes.fromhex('20008052') + branch(0x3b4cc, 0x3b598),
       'Bypass signer rejection notifier and process termination; return true')
    # Two rejection branches in the watchdog: use its existing void epilogue.
    at(0x3e478, bytes.fromhex('e10b40f9'), branch(0x3e478, 0x3e550),
       'Bypass watchdog notifier and kill; preserve the normal native initializer')
    at(0x3e4d0, bytes.fromhex('1f2003d5'), branch(0x3e4d0, 0x3e550),
       'Bypass second watchdog rejection branch')
    return bytes(out), edits
