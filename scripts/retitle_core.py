"""Title-only zip rewrite. Every member except listing.txt is copied byte-for-byte (raw compressed data);
listing.txt is stored uncompressed with the new TITLE line, so the output is deterministic on any machine."""
import io, re, struct, zipfile, zlib

def _dos(dt):
    y, mo, d, h, mi, s = dt
    return ((h << 11) | (mi << 5) | (s // 2), ((y - 1980) << 9) | (mo << 5) | d)

def retitle(src: bytes, new_title: str, expect_old: str = None) -> bytes:
    zf = zipfile.ZipFile(io.BytesIO(src))
    out = io.BytesIO(); cen = []
    for info in zf.infolist():
        name = info.filename.encode('utf-8')
        if info.filename.endswith('/listing.txt'):
            s = zf.read(info.filename).decode('utf-8')
            m = re.search(r'^TITLE\n(.*?)  \((\d+) chars\)\n', s, re.M)
            assert m, 'no TITLE block'
            if expect_old is not None: assert m.group(1) == expect_old, (m.group(1), expect_old)
            s = s[:m.start()] + 'TITLE\n%s  (%d chars)\n' % (new_title, len(new_title)) + s[m.end():]
            data = s.encode('utf-8'); method = 0; crc = zlib.crc32(data) & 0xffffffff; csize = usize = len(data)
        else:
            off = info.header_offset
            sig, ver, fl, meth, t, d, c, cs, us, nl, el = struct.unpack('<4s5H3L2H', src[off:off + 30])
            assert sig == b'PK\x03\x04' and meth == info.compress_type
            st = off + 30 + nl + el
            data = src[st:st + info.compress_size]; method = info.compress_type; crc = info.CRC; csize = info.compress_size; usize = info.file_size
        t, d = _dos(info.date_time); flags = 0x800 if any(b > 127 for b in name) else 0
        pos = out.tell()
        out.write(struct.pack('<4s5H3L2H', b'PK\x03\x04', 20, flags, method, t, d, crc, csize, usize, len(name), 0)); out.write(name); out.write(data)
        cen.append((name, flags, method, t, d, crc, csize, usize, info.external_attr, pos))
    cstart = out.tell()
    for name, flags, method, t, d, crc, csize, usize, ea, pos in cen:
        out.write(struct.pack('<4s6H3L5H2L', b'PK\x01\x02', (3 << 8) | 20, 20, flags, method, t, d, crc, csize, usize, len(name), 0, 0, 0, 0, ea, pos)); out.write(name)
    csz = out.tell() - cstart
    out.write(struct.pack('<4s4H2LH', b'PK\x05\x06', 0, 0, len(cen), len(cen), csz, cstart, 0))
    return out.getvalue()
