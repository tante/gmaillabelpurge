# The contents of this file has been derived code from the
# Twisted project at revision 36933 (http://twistedmatrix.com/).
# The original author is Jp Calderone.

# Twisted project license follows:

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import codecs

# we need to cast Python >=3.3 memoryview to chars (from unsigned bytes), but
# cast is absent in previous versions: thus, the lambda returns the 
# memoryview instance while ignoring the format
memory_cast = getattr(memoryview, "cast", lambda *x: x[0])

def modified_base64(s):
    s_utf7 = s.encode('utf-7')
    return s_utf7[1:-1].replace(b'/', b',')

def modified_unbase64(s):
    s_utf7 = b'+' + s.replace(b',', b'/') + b'-'
    return s_utf7.decode('utf-7')

def encoder(s, errors=None):
    """
    Encode the given C{unicode} string using the IMAP4 specific variation of
    UTF-7.

    @type s: C{unicode}
    @param s: The text to encode.

    @param errors: Policy for handling encoding errors.  Currently ignored.

    @return: C{tuple} of a C{bytes} giving the encoded bytes and an C{int}
        giving the number of code units consumed from the input.
    """
    r = bytearray()
    _in = []
    valid_chars = set(map(chr, range(0x20,0x7f))) - {"&"}
    for c in s:
        if c in valid_chars:
            if _in:
                r += b'&' + modified_base64(''.join(_in)) + b'-'
                del _in[:]
            r.append(ord(c))
        elif c == '&':
            if _in:
                r += b'&' + modified_base64(''.join(_in)) + b'-'
                del _in[:]
            r += b'&-'
        else:
            _in.append(c)
    if _in:
        r.extend(b'&' + modified_base64(''.join(_in)) + b'-')
    return (bytes(r), len(s))

def decoder(s, errors=None):
    """
    Decode the given C{bytes} using the IMAP4 specific variation of UTF-7.

    @type s: C{bytes}
    @param s: The bytes to decode.

    @param errors: Policy for handling decoding errors.  Currently ignored.

    @return: a C{tuple} of a C{unicode} string giving the text which was
        decoded and an C{int} giving the number of bytes consumed from the
        input.
    """
    r = []
    decode = []
    s = memory_cast(s, 'c')
    for c in s:
        if c == b'&' and not decode:
            decode.append('&')
        elif c == b'-' and decode:
            if len(decode) == 1:
                r.append('&')
            else:
                r.append(modified_unbase64(b''.join(decode[1:])))
            decode = []
        elif decode:
            decode.append(c)
        else:
            r.append(c.decode())
    if decode:
        r.append(modified_unbase64(b''.join(decode[1:])))
    return (''.join(r), len(s))

class StreamReader(codecs.StreamReader):
    def decode(self, s, errors='strict'):
        return decoder(s)

class StreamWriter(codecs.StreamWriter):
    def encode(self, s, errors='strict'):
        return encoder(s)

_codecInfo = (encoder, decoder, StreamReader, StreamWriter)
try:
    _codecInfoClass = codecs.CodecInfo
except AttributeError:
    pass
else:
    _codecInfo = _codecInfoClass(*_codecInfo)

def imap4_utf_7(name):
    if name == 'imap4-utf-7':
        return _codecInfo
codecs.register(imap4_utf_7)
