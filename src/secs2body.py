import os
import struct

class Secs2BodyParseError(Exception):
    pass

class Secs2BodySmlParseError(Secs2BodyParseError):
    pass

class Secs2BodyBytesParseError(Secs2BodyParseError):
    pass

class Secs2Body:

    _ITEMS = (
        ('L',       0x00, -1, None),
        ('B',       0x20,  1, 'c'),
        ('BOOLEAN', 0x24,  1, '?'),
        ('A',       0x40, -1, None),
        ('I8',      0x60,  8, 'q'),
        ('I1',      0x64,  1, 'b'),
        ('I2',      0x68,  2, 'h'),
        ('I4',      0x70,  4, 'l'),
        ('F8',      0x80,  8, 'd'),
        ('F4',      0x90,  4, 'f'),
        ('U8',      0xA0,  8, 'Q'),
        ('U1',      0xA4,  1, 'B'),
        ('U2',      0xA8,  2, 'H'),
        ('U4',      0xB0,  4, 'L')
    )
    _BYTES_LEN_3 = 2**16
    _BYTES_LEN_2 = 2**8
    _SML_TAB = '  '
    _SML_VALUESEPARATOR = ' '
    _SML_LINESEPARATOR = os.linesep

    def __init__(self, item_type, value):

        if item_type is None:
            raise TypeError("Not accept None")

        tt = type(item_type)

        if tt is str:
            self._type = self._get_item_type_from_sml(item_type)
        elif tt is tuple:
            self._type = item_type
        else:
            raise TypeError("Require str or tuple")

        def _tiof(value, item_size, is_signed):    # test_int_overflow return int_value

            if type(value) is str and value.upper().startswith("0X"):
                v = int(value[2:], 16)
            else:
                v = int(value)

            n = item_size * 8

            if is_signed:
                n -= 1
            
            x = 2**n
            max = x-1
            
            if is_signed:
                min = -x
            else:
                min = 0
            
            if v > max or v < min:
                raise ValueError("value is from " + str(min) + " to " + str(max) + ", value is " + str(v))

            return v

        tv = type(value)

        if self._type[0] == 'L':

            if tv is tuple or tv is list:
                vv = list()
                for x in value:
                    tx = type(x)
                    if tx is Secs2Body:
                        vv.append(x)
                    elif (tx is tuple or tx is list) and (len(x) == 2):
                        vv.append(Secs2Body(x[0], x[1]))
                    else:
                        raise TypeError("L value require tuple or list, and length == 2")

                self._value = tuple(vv)

            else:
                raise TypeError("L values require tuple or list")
        
        elif self._type[0] == 'BOOLEAN':

            if tv is tuple or tv is list:
                self._value = tuple([bool(x) for x in value])
            else:
                self._value = tuple([bool(value)])

        elif self._type[0] == 'A':
            self._value = str(value)

        elif self._type[0] == 'B':

            if tv is bytes:
                self._value = value
            elif tv is bytearray:
                self._value = bytes(value)
            elif tv is tuple or tv is list:
                self._value = bytes([(_tiof(x, self._type[2], False)) for x in value])
            else:
                self._value = bytes([_tiof(value, self._type[2], False)])

        elif self._type[0] in ('U1', 'U2', 'U4', 'U8'):

            if tv is tuple or tv is list:
                self._value = tuple([(_tiof(x, self._type[2], False)) for x in value])
            else:
                self._value = tuple([_tiof(value, self._type[2], False)])

        elif self._type[0] in ('I1', 'I2', 'I4', 'I8'):

            if tv is tuple or tv is list:
                self._value = tuple([(_tiof(x, self._type[2], True)) for x in value])
            else:
                self._value = tuple((_tiof(value, self._type[2], True), ))

        elif self._type[0] in ('F4', 'F8'):

            if tv is tuple or tv is list:
                self._value = tuple([float(x) for x in value])
            else:
                self._value = tuple((float(value), ))

        self._cache_sml = None
        self._cache_repr = None
        self._cache_bytes = None


    def __str__(self):
        return self.to_sml()

    def __repr__(self):
        if self._cache_repr is None:
            self._cache_repr = str((self._type[0], self._value))
        return self._cache_repr

    def __len__(self):
        return len(self._value)

    def __getitem__(self, item):
        return self._value[item]

    def __iter__(self):
        return iter(self._value)

    def __next__(self):
        return next(self._value)

    def get_type(self):
        return self._type[0]
    
    def to_sml(self):

        def _ss(item_type, length, value):  # create_sml_string
            return '<' + item_type + ' [' + str(length) + '] ' + value + ' >'

        def _lsf(value, level=''):  # create_list_sml_string

            deep_level = level + self._SML_TAB

            vv = list()
            vv.append(level + '<L [' + str(len(value)) + ']')

            for x in value:
                if x._type[0] == 'L':
                    vv.append(_lsf(x._value, deep_level))
                else:
                    vv.append(deep_level + x.to_sml())

            vv.append(level + '>')
            return self._SML_LINESEPARATOR.join(vv)

        if self._cache_sml is None:

            if self._type[0] == 'L':
                self._cache_sml = _lsf(self._value)

            elif self._type[0] == 'BOOLEAN':
                vv = [("TRUE" if x else "FALSE") for x in self._value]
                self._cache_sml = _ss(
                    self._type[0],
                    len(vv),
                    self._SML_VALUESEPARATOR.join(vv))

            elif self._type[0] == 'A':
                self._cache_sml = _ss(
                    self._type[0],
                    len(self._value),
                    '"' + self._value + '"')

            elif self._type[0] == 'B':
                vv = [('0x' + '{:02X}'.format(x)) for x in self._value]
                self._cache_sml = _ss(
                    self._type[0],
                    len(vv),
                    self._SML_VALUESEPARATOR.join(vv))

            elif self._type[0] in ('I1', 'I2', 'I4', 'I8', 'U1', 'U2', 'U4', 'U8', 'F4', 'F8'):
                vv = [str(x) for x in self._value]
                self._cache_sml = _ss(
                    self._type[0],
                    len(vv),
                    self._SML_VALUESEPARATOR.join(vv))

        return self._cache_sml

    def to_bytes(self):

        def _ihb(item_type_byte, value_length):   # create_item_header_bytes
            bs = struct.pack('>L', value_length)
            if value_length >= self._BYTES_LEN_3:
                return struct.pack('>B', (item_type_byte | 0x03)) + bs[1:4]
            elif value_length >= self._BYTES_LEN_2:
                return struct.pack('>B', (item_type_byte | 0x02)) + bs[2:4]
            else:
                return struct.pack('>B', (item_type_byte | 0x01)) + bs[3:4]

        if self._cache_bytes is None:

            if self._type[0] == 'L':
                vv = [x.to_bytes() for x in self._value]
                self._cache_bytes = _ihb(self._type[1], len(self._value)) + b''.join(vv)

            elif self._type[0] == 'BOOLEAN':
                vv = [(0xFF if f else 0x00) for f in self._value]
                self._cache_bytes = _ihb(self._type[1], len(vv)) + bytes(vv)

            elif self._type[0] == 'A':
                bs = self._value.encode(encoding='ascii')
                self._cache_bytes = _ihb(self._type[1], len(bs)) + bs

            elif self._type[0] == 'B':
                self._cache_bytes = _ihb(self._type[1], len(self._value)) + self._value

            elif self._type[0] in ('I1', 'I2', 'I4', 'I8', 'F8', 'F4', 'U1', 'U2', 'U4', 'U8'):
                bs = b''.join([struct.pack(('>' + self._type[3]), x) for x in self._value])
                self._cache_bytes = _ihb(self._type[1], len(bs)) + bs

        return self._cache_bytes

    @classmethod
    def _get_item_type_from_sml(cls, sml_item_type):
        str_upper = sml_item_type.upper()
        for i in cls._ITEMS:
            if i[0] == str_upper:
                return i
        raise ValueError("'" + sml_item_type + "' not found")

    @classmethod
    def from_body_sml(cls, sml_str):

        def _is_ws(v):  # is_white_space
            return (v.encode(encoding='ascii'))[0] <= 0x20

        def _seek_next(s, from_pos, *args):
            p = from_pos
            if len(args) > 0:
                while True:
                    v = s[p]
                    for a in args:
                        if type(a) is str:
                            if v == a:
                                return (v, p)
                        else:
                            if a(v):
                                return (v, p)
                    p += 1
            else:
                while True:
                    v = s[p]
                    if _is_ws(v):
                        p += 1
                    else:
                        return (v, p)

        def _ssbkt(s, from_pos):    # seek size_start_blacket'[' position, return position, -1 if not exist
            v, p = _seek_next(s, from_pos)
            return p if v == '[' else -1

        def _sebkt(s, from_pos):    # seek size_end_blacket']' position, return position
            return (_seek_next(s, from_pos, ']'))[1]

        def _isbkt(s, from_pos):    # seek item_start_blacket'<' position, return position, -1 if not exist
            v, p = _seek_next(s, from_pos)
            return p if v == '<' else -1

        def _iebkt(s, from_pos):    # seek item_end_blacket'>' position, return position
            return (_seek_next(s, from_pos, '>'))[1]

        def _seek_item(s, from_pos):  # seek item_type, return (item_type, shifted_position)
            p_start = (_seek_next(s, from_pos))[1]
            p_end = (_seek_next(s, (p_start + 1), '[', '"', '<', '>', _is_ws))[1]
            return (cls._get_item_type_from_sml(s[p_start:p_end]), p_end)

        def _f(s, from_pos):

            p = _isbkt(s, from_pos)

            if p < 0:
                raise Secs2BodySmlParseError("Not start < bracket")

            tt, p = _seek_item(s, (p + 1))

            r = _ssbkt(s, p)
            if r >= 0:
                p = _sebkt(s, (r + 1)) + 1
            
            if tt[0] == 'L':
                vv = list()
                while True:
                    v, p = _seek_next(s, p)
                    if v == '>':
                        return (Secs2Body(tt, vv), (p + 1))

                    elif v == '<':
                        r, p = _f(s, p)
                        vv.append(r)

                    else:
                        raise Secs2BodySmlParseError("Not reach LIST end")

            elif tt[0] == 'BOOLEAN':
                r = _iebkt(s, p)
                vv = list()
                for x in s[p:r].strip().split():
                    ux = x.upper()
                    if ux == 'TRUE' or ux == 'T':
                        vv.append(True)
                    elif ux == 'FALSE' or ux == 'F':
                        vv.append(False)
                    else:
                        raise Secs2BodySmlParseError("Not accept, BOOELAN require TRUE or FALSE")
                return (Secs2Body(tt, vv), (r + 1))

            elif tt[0] == 'A':
                vv = list()
                while True:
                    v, p_start = _seek_next(s, p)
                    if v == '>':
                        return (Secs2Body(tt, ''.join(vv)), (p_start + 1))
 
                    elif v == '"':
                        v, p_end = _seek_next(s, (p_start + 1), '"')
                        vv.append(s[(p_start+1):p_end])
                        p = p_end + 1

                    elif v == '0':
                        if s[p_start + 1] not in ('X', 'x'):
                            raise Secs2BodyParseError("Ascii not accept 0xNN")
                        v, p = _seek_next(s, (p_start+2), '"', '>', _is_ws)
                        vv.append(bytes([int(s[(p_start+2):p], 16)]).decode(encoding='ascii'))

                    else:
                        raise Secs2BodySmlParseError("Ascii not reach end")

            elif tt[0] in ('B', 'I1', 'I2', 'I4', 'I8', 'F4', 'F8', 'U1', 'U2', 'U4', 'U8'):
                r = _iebkt(s, p)
                return (Secs2Body(tt, s[p:r].strip().split()), (r + 1))

        try:
            if sml_str is None:
                raise Secs2BodySmlParseError("Not accept None")
            
            ss = str(sml_str).strip()
            r, p = _f(ss, 0)
            if len(ss[p:]) > 0:
                raise Secs2BodySmlParseError("Not reach end, end=" + str(p) + ", length=" + str(len(ss)))
            return r

        except TypeError as e:
            raise Secs2BodySmlParseError(str(e))
        except ValueError as e:
            raise Secs2BodySmlParseError(str(e))
        except IndexError as e:
            raise Secs2BodySmlParseError(str(e))

    @classmethod
    def from_body_bytes(cls, body_bytes):

        def _itr(b):    # get_item_type
            x = b & 0xFC
            for i in cls._ITEMS:
                if i[1] == x:
                    return i
            raise ValueError('0x' + '{:02X}'.format(b) + " not found")

        def _xr(bs, pos):   # get (item_type, value_length, shift_position)

            b = bs[pos]
            t = _itr(b)
            len_bit = b & 0x3

            if len_bit == 3:
                len = (bs[pos+1] << 16) | (bs[pos+2] << 8) | bs[pos+3]
            elif len_bit == 2:
                len = (bs[pos+1] << 8) | bs[pos+2]
            else:
                len = bs[pos+1]

            return (t, len, (len_bit + 1))

        def _f(bs, pos):

            r = _xr(bs, pos)
            tt, v_len, b_len = _xr(bs, pos)
            start_index = pos + b_len
            end_index = pos + b_len + v_len

            if tt[0] == 'L':
                vv = list()
                p = start_index
                for _ in range(r[1]):
                    v, p = _f(bs, p)
                    vv.append(v)
                return (Secs2Body(tt, vv), p)

            elif tt[0] == 'BOOLEAN':
                vv = [(b != 0x00) for b in bs[start_index:end_index]]
                return (Secs2Body(tt, vv), end_index)

            elif tt[0] == 'A':
                v = bs[start_index:end_index].decode(encoding='ascii')
                return (Secs2Body(tt, v), end_index)

            elif tt[0] == 'B':
                vv = bs[start_index:end_index]
                return (Secs2Body(tt, vv), end_index)

            elif tt[0] in ('I1', 'I2', 'I4', 'I8', 'F8', 'F4', 'U1', 'U2', 'U4', 'U8'):
                vv = list()
                p = start_index
                for _ in range(0, v_len, tt[2]):
                    prev = p
                    p += tt[2]
                    v = struct.unpack(('>' + tt[3]), bs[prev:p])
                    vv.append(v[0])
                return (Secs2Body(tt, vv), end_index)

        try:
            r, p = _f(body_bytes, 0)
            length = len(body_bytes)

            if p == length:
                r._cache_bytes = bytes(body_bytes)
                return r
            else:
                raise Secs2BodyBytesParseError("not reach bytes end, reach=" + str(p) + ", length=" + str(length))

        except ValueError as e:
            raise Secs2BodyBytesParseError(str(e))
        except TypeError as e:
            raise Secs2BodyBytesParseError(str(e))
        except IndexError as e:
            raise Secs2BodyBytesParseError(str(e))


if __name__ == '__main__':

    print('')
    print("try-python")

#    s = Secs2Body({"aaa":111})

    vv = tuple([
        # Secs2Body('A', 'ASCII-VALUE'),
        # Secs2Body('B', 1),
        # Secs2Body('B', (0x01, 0x10, 0xAA, 0xFF)),
        # Secs2Body('BOOLEAN', True),
        # Secs2Body('BOOLEAN', (True, False, True)),
        # Secs2Body('I1', 100),
        # Secs2Body('I1', (100, -120)),
        # Secs2Body('U4', 2000),
        # Secs2Body('U2', (2000, 3000)),
        # Secs2Body('F4', 10.0),
#        Secs2Body('F4', (10.0, 20.0, -30.0)),
    
        Secs2Body('L', (
            ('B', (0xFF, 0x01)),
            ('B', []),
            ('A', 'CCC_DDD'),
            ('I2', [100, -200, -300]),
            ('U4', [100, 200, 300]),
            ('L', [
                ('BOOLEAN', True),
                ('U4', 12345)
                ]),
            ('L', [])
            ))
    ])

    # for v in vv:
    #     print(v)
    #     print(repr(v))

    # a = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    # v = Secs2Body('A', a+a+a+a+a+a+a+a+a+a)
    # v = Secs2Body('B', [0x00, 0xFF, 0x1, 0x2])
    # v = Secs2Body('BOOLEAN', (True, False))
    # v = Secs2Body('U2', (1, 2, 3))
    # v = Secs2Body('I2', (-1, 2, -3))
    # v = Secs2Body('F8', (10.0, 20.0))
    v = Secs2Body('L', [
        ('L', [
            ('B', [0x01, 0xFF]),
            ('BOOLEAN', [True, False]),
            ('L', [])
        ]),
        ('B', [0x01, 0x10]),
        ('A', "ABCDEF"),
        ('U2', [1,2,3]),
        ('I2', [-100,200,-300]),
        ('F4', [19.00, -29.00])
        ])

    bs = v.to_bytes()
    print(bs)
    
    r = Secs2Body.from_body_bytes(bs)
    print(r)

    x = Secs2Body.from_body_sml(r.to_sml())
    print(x)

    print(x.to_bytes())

    # print('length: ' + str(len(x)))

    # for a in x:
    #     print(a.get_type() + ': ' + str(a._value))
    #     for b in a:
    #         print(b)

    # print(x[0][1][1])

    # v = Secs2Body.from_body_sml('<A [10] "XYZ123" 0x61 0x20 "ABC">')
    # v = Secs2Body.from_body_sml('<BOOLEAN[2] TRUE FALSE>')
    # v = Secs2Body.from_body_sml('<B 0x0A 0x02>')
    # v = Secs2Body.from_body_sml('<U2 100 200>')
    # v = Secs2Body.from_body_sml('<L <A "AAA" 0x42\t0x43"124" ><L <I1 1><I2 100>><B 0x0><BOOLEAN TRUE><F4 -10.0>>')
    # print(v)

    # try:
    #     bs = v.to_bytes()
    #     print(bs)
        
    #     r = Secs2Body.from_body_bytes(bs)
    #     print(r)

    # except Secs2BodyParseError as e:
    #     print("Secs2BodyParserError: " + str(e))
