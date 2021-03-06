from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception('Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s' % kaitaistruct.__version__)
from . import eink_wbf_wav_addrs_collection
from . import eink_wbf_wav_addrs_collection
from . import bcd

class EinkWbf(KaitaiStruct):
    """`.wbf` is the format stored on the flash chip present on the ribbon cable of some electronic paper displays made by the E Ink Corporation and `.wrf` is the input format used by the i.MX 508 EPDC (electronic paper display controller) and possibly the EPDCs of later i.MX chipsets.
    
    `inkwave` is a command-line utility for converting `.wbf` to `.wrf` files and displaying meta-data information from `.wbf` and `.wrf` files in a human readable format.
    
    In order to make full use of these displays it is necessary to read the `.wbf` data from the SPI flash chip, convert it to `.wrf` format and then pass it to the EPDC kernel module. Also in some firmwares the files are stored as they are.
    
    # Limitations and unsolved mysteries
    * https://github.com/kaitai-io/kaitai_struct/issues/815 . Partially overcome by `fixEnums` postprocessor.
    * The spec is currently not expressed entirely in KS, as the original code takes 2 passes, the first pass creates the state (`wav_addrs` array, you must pass it to `eink_wbf::temp_range` as a param of type `eink_wbf_wav_addrs_collection` (see the python file for the example of its impl)) used by the second pass. I don't beleive the format was really designed like that and I feel like it can be possible to get rid of the first pass and express the format entirely in KS, but it has not yet been done.
    * Again, the code within `inkwave` looks unnecessary complex, and this complexity has been transfered to this spec. I feel like it can be simplified a lot, but it has not yet been done.
    * `bits_per_pixel`
    * `mysterious_offset`
    * structure of `advanced_wfm_flags` is unknown
    * Each waveform segment (WUT?) ends with two bytes that do not appear to be part of the waveform itself. The first is always `0xff` and the second is unpredictable. Unfortunately `0xff` can occur inside of waveforms as well so it is not useful as an endpoint marker. The last byte might be a sort of checksum but does not appear to be a simple 1-byte sum like other 1-byte checksums used in .wbf files.
    
    .. seealso::
       Source - https://github.com/fread-ink/inkwave
    
    
    .. seealso::
       Source - https://github.com/KOLANICH-tools/inkwave.py
    
    
    .. seealso::
       Source - https://web.archive.org/web/http://essentialscrap.com/eink/
    
    
    .. seealso::
       Source - https://web.archive.org/web/20200206095814/http://git.spritesserver.nl/espeink.git/
    
    
    .. seealso::
       Source - https://github.com/julbouln/ice40_eink_controller/tree/master/utils/wbf_dump
    """

    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()
        self.debug = False

    def _read(self):
        self.header = EinkWbf.Header(self._io, self, self._root)
        self.temp_range_table = EinkWbf.TempRangeTable(self._io, self, self._root)

    class WavAddrsCollection(KaitaiStruct):
        """A fake type that is not used, which only purpose is to calm down KSC in order to allow us to pass a custom opaque type needed by `calc_length`. Currently it won't work on strictly typed languages. It should be fixed by `interfaces` proposal."""

        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.arr = [None] * 0
            for i in range(0):
                self.arr[i] = self._io.read_u4le()

    class TempRangeTable(KaitaiStruct):

        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.ranges = [None] * (self._root.header.temperature_range_count + 1)
            for i in range(self._root.header.temperature_range_count + 1):
                self.ranges[i] = EinkWbf.TempRangeTable.Range(i, self._io, self, self._root)
            self.checksum = self._io.read_u1()
            _ = self.checksum
            if not _ == self.calculated_checksum:
                raise kaitaistruct.ValidationExprError(self.checksum, self._io, u'/types/temp_range_table/seq/1')

        class Range(KaitaiStruct):

            def __init__(self, idx, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self.idx = idx
                self._read()

            def _read(self):
                if self.is_full:
                    self.start_own = self._io.read_u1()
                self.stop = self._io.read_u1()

            @property
            def is_full(self):
                if hasattr(self, '_m_is_full'):
                    return self._m_is_full if hasattr(self, '_m_is_full') else None
                self._m_is_full = self.idx == 0
                return self._m_is_full if hasattr(self, '_m_is_full') else None

            @property
            def start(self):
                if hasattr(self, '_m_start'):
                    return self._m_start if hasattr(self, '_m_start') else None
                self._m_start = self.start_own if self.is_full else self._parent.ranges[self.idx - 1].stop
                return self._m_start if hasattr(self, '_m_start') else None

            @property
            def checksum(self):
                if hasattr(self, '_m_checksum'):
                    return self._m_checksum if hasattr(self, '_m_checksum') else None
                self._m_checksum = (self.start_own if self.is_full else self._parent.ranges[self.idx - 1].checksum) + self.stop & 255
                return self._m_checksum if hasattr(self, '_m_checksum') else None

        @property
        def calculated_checksum(self):
            if hasattr(self, '_m_calculated_checksum'):
                return self._m_calculated_checksum if hasattr(self, '_m_calculated_checksum') else None
            self._m_calculated_checksum = self.ranges[len(self.ranges) - 1].checksum
            return self._m_calculated_checksum if hasattr(self, '_m_calculated_checksum') else None

    class ChecksummedPtr(KaitaiStruct):
        """Pointer with checksum."""

        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.raw = self._io.read_u4le()
            self.validate_checksum = EinkWbf.Passthrough(self.checksum, self._io, self, self._root)
            _ = self.validate_checksum
            if not _.value == self.computed_checksum:
                raise kaitaistruct.ValidationExprError(self.validate_checksum, self._io, u'/types/checksummed_ptr/seq/1')

        @property
        def ptr(self):
            if hasattr(self, '_m_ptr'):
                return self._m_ptr if hasattr(self, '_m_ptr') else None
            self._m_ptr = self.raw & 16777215
            return self._m_ptr if hasattr(self, '_m_ptr') else None

        @property
        def checksum(self):
            if hasattr(self, '_m_checksum'):
                return self._m_checksum if hasattr(self, '_m_checksum') else None
            self._m_checksum = self.raw >> 24
            return self._m_checksum if hasattr(self, '_m_checksum') else None

        @property
        def computed_checksum(self):
            if hasattr(self, '_m_computed_checksum'):
                return self._m_computed_checksum if hasattr(self, '_m_computed_checksum') else None
            self._m_computed_checksum = (self.ptr & 255) + (self.ptr >> 8 & 255) + (self.ptr >> 16 & 255) & 255
            return self._m_computed_checksum if hasattr(self, '_m_computed_checksum') else None

    class Mode(KaitaiStruct):

        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.ptr = EinkWbf.ChecksummedPtr(self._io, self, self._root)
            self._unnamed1 = EinkWbf.Mode.UnlazyRanges(self._io, self, self._root)

        class UnlazyRanges(KaitaiStruct):
            """It causes parsing of `ranges` array, this way populating `_root.wav_addrs_external` and doing the first pass
            """

            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._read()

            def _read(self):
                if len(self._parent.ranges.ranges) != 0:
                    self._unnamed0 = self._io.read_bytes(0)

        class TempRanges(KaitaiStruct):

            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._read()

            def _read(self):
                self.ranges = [None] * (self._root.header.temperature_range_count + 1)
                for i in range(self._root.header.temperature_range_count + 1):
                    self.ranges[i] = EinkWbf.Mode.TempRanges.TempRange(self._io, self, self._root)

            class TempRange(KaitaiStruct):

                def __init__(self, _io, _parent=None, _root=None):
                    self._io = _io
                    self._parent = _parent
                    self._root = _root if _root else self
                    self._read()

                def _read(self):
                    self.wav_addr = EinkWbf.ChecksummedPtr(self._io, self, self._root)
                    self._unnamed1 = eink_wbf_wav_addrs_collection.EinkWbfWavAddrsCollection.Add(self.wav_addr.ptr, self._root.wav_addrs_external, self._io)

                class CalcLength(KaitaiStruct):

                    def __init__(self, _io, _parent=None, _root=None):
                        self._io = _io
                        self._parent = _parent
                        self._root = _root if _root else self
                        self._read()

                    def _read(self):
                        pass

                    class SearchIteration(KaitaiStruct):

                        def __init__(self, i, _io, _parent=None, _root=None):
                            self._io = _io
                            self._parent = _parent
                            self._root = _root if _root else self
                            self.i = i
                            self._read()

                        def _read(self):
                            pass

                        @property
                        def is_over(self):
                            if hasattr(self, '_m_is_over'):
                                return self._m_is_over if hasattr(self, '_m_is_over') else None
                            self._m_is_over = self.i == len(self._parent._parent.wav_addrs.arr) - 2
                            return self._m_is_over if hasattr(self, '_m_is_over') else None

                        @property
                        def next_addr(self):
                            if hasattr(self, '_m_next_addr'):
                                return self._m_next_addr if hasattr(self, '_m_next_addr') else None
                            self._m_next_addr = self._parent._parent.wav_addrs.arr[self.i + 1]
                            return self._m_next_addr if hasattr(self, '_m_next_addr') else None

                        @property
                        def addr(self):
                            if hasattr(self, '_m_addr'):
                                return self._m_addr if hasattr(self, '_m_addr') else None
                            self._m_addr = self._parent._parent.wav_addrs.arr[self.i]
                            return self._m_addr if hasattr(self, '_m_addr') else None

                        @property
                        def size(self):
                            if hasattr(self, '_m_size'):
                                return self._m_size if hasattr(self, '_m_size') else None
                            if self.is_found:
                                self._m_size = self._parent._parent.wav_addrs.arr[self.i + 1] - self._parent._parent.wav_addr.ptr
                            return self._m_size if hasattr(self, '_m_size') else None

                        @property
                        def is_found(self):
                            if hasattr(self, '_m_is_found'):
                                return self._m_is_found if hasattr(self, '_m_is_found') else None
                            self._m_is_found = self.addr == self._parent._parent.wav_addr.ptr
                            return self._m_is_found if hasattr(self, '_m_is_found') else None

                        @property
                        def is_terminator(self):
                            if hasattr(self, '_m_is_terminator'):
                                return self._m_is_terminator if hasattr(self, '_m_is_terminator') else None
                            self._m_is_terminator = self.addr == 0
                            return self._m_is_terminator if hasattr(self, '_m_is_terminator') else None

                    @property
                    def max_waveforms(self):
                        """there probably aren't any displays with more waveforms than this (we hope)
                        (technically the header allows for 256 * 256 waveforms but that's not realistic)
                        """
                        if hasattr(self, '_m_max_waveforms'):
                            return self._m_max_waveforms if hasattr(self, '_m_max_waveforms') else None
                        self._m_max_waveforms = 4096
                        return self._m_max_waveforms if hasattr(self, '_m_max_waveforms') else None

                    @property
                    def search(self):
                        if hasattr(self, '_m_search'):
                            return self._m_search if hasattr(self, '_m_search') else None
                        _pos = self._io.pos()
                        self._io.seek(0)
                        self._m_search = []
                        i = 0
                        while True:
                            _ = EinkWbf.Mode.TempRanges.TempRange.CalcLength.SearchIteration(i, self._io, self, self._root)
                            self._m_search.append(_)
                            if _.is_over or _.is_terminator or _.is_found:
                                break
                            i += 1
                        self._io.seek(_pos)
                        return self._m_search if hasattr(self, '_m_search') else None

                    @property
                    def size(self):
                        if hasattr(self, '_m_size'):
                            return self._m_size if hasattr(self, '_m_size') else None
                        self._m_size = self.search[len(self.search) - 1].size
                        return self._m_size if hasattr(self, '_m_size') else None

                class Waveform(KaitaiStruct):

                    def __init__(self, _io, _parent=None, _root=None):
                        self._io = _io
                        self._parent = _parent
                        self._root = _root if _root else self
                        self._read()

                    def _read(self):
                        self.waveform = []
                        i = 0
                        while not self._io.is_eof():
                            self.waveform.append(EinkWbf.Mode.TempRanges.TempRange.Waveform.WaveformPiece(i, self._io, self, self._root))
                            i += 1

                    class WaveformPiece(KaitaiStruct):

                        def __init__(self, k, _io, _parent=None, _root=None):
                            self._io = _io
                            self._parent = _parent
                            self._root = _root if _root else self
                            self.k = k
                            self._read()

                        def pp(self, *args, **kwargs):
                            if self._root.debug and self.k >= 0:
                                print(*args, **kwargs)

                        def _read(self):
                            if not self.is_end_of_stream:
                                self.current_byte = self._io.read_u1()
                                if self._root.debug:
                                    print('{}, {}'.format(self._io.pos() - 1, hex(self.current_byte)[2:]))
                                if not self.is_terminator:
                                    self.pp('s', (self.s.s0, self.s.s1, self.s.s2, self.s.s3), self.k)
                            if self.should_read_count:
                                self.count_read = self._io.read_u1()
                            if not self.is_terminator:
                                self.pp('count {:d}'.format(self.count), self.k)

                        @property
                        def is_first(self):
                            if hasattr(self, '_m_is_first'):
                                return self._m_is_first if hasattr(self, '_m_is_first') else None
                            self._m_is_first = self.k == 0
                            return self._m_is_first if hasattr(self, '_m_is_first') else None

                        @property
                        def count(self):
                            """if `is_end_of_stream` is `false` and `should_read_count` is `true`, `count_read` still must be read, but it seems it is discarded. Maybe in that case it serves some other purpose."""
                            if hasattr(self, '_m_count'):
                                return self._m_count if hasattr(self, '_m_count') else None
                            self._m_count = (1 if self.fc_active else 1 if self.is_end_of_stream else self.count_read + 1) if not self.is_terminator else 0 if self.is_first else self._parent.waveform[self.k - 1].count
                            return self._m_count if hasattr(self, '_m_count') else None

                        @property
                        def is_end_of_stream(self):
                            if hasattr(self, '_m_is_end_of_stream'):
                                return self._m_is_end_of_stream if hasattr(self, '_m_is_end_of_stream') else None
                            self._m_is_end_of_stream = self._io.pos() >= self._parent._parent.l
                            return self._m_is_end_of_stream if hasattr(self, '_m_is_end_of_stream') else None

                        @property
                        def s(self):
                            if hasattr(self, '_m_s'):
                                return self._m_s if hasattr(self, '_m_s') else None
                            _pos = self._io.pos()
                            self._io.seek(0)
                            self._m_s = EinkWbf.Mode.TempRanges.TempRange.Waveform.PackedState(self.current_byte, self._io, self, self._root)
                            self._io.seek(_pos)
                            return self._m_s if hasattr(self, '_m_s') else None

                        @property
                        def is_terminator(self):
                            """0xfc is a start and end tag for a section
                            of one-byte bit-patterns with an assumed count of 1
                            """
                            if hasattr(self, '_m_is_terminator'):
                                return self._m_is_terminator if hasattr(self, '_m_is_terminator') else None
                            self._m_is_terminator = self.current_byte == 252
                            return self._m_is_terminator if hasattr(self, '_m_is_terminator') else None

                        @property
                        def fc_active(self):
                            """`is_first?is_terminator` is because `fc_active` is set to `false` initially, then it is flipped if `is_terminator`, so essentially it is `fc_active = fc_active xor is_terminator`, and for the first iteration `fc_active = false xor is_terminator = is_terminator`
                            """
                            if hasattr(self, '_m_fc_active'):
                                return self._m_fc_active if hasattr(self, '_m_fc_active') else None
                            self._m_fc_active = self.is_terminator if self.is_first else not self._parent.waveform[self.k - 1].fc_active if self.is_terminator else self._parent.waveform[self.k - 1].fc_active
                            return self._m_fc_active if hasattr(self, '_m_fc_active') else None

                        @property
                        def zero_pad(self):
                            if hasattr(self, '_m_zero_pad'):
                                return self._m_zero_pad if hasattr(self, '_m_zero_pad') else None
                            if not self.is_terminator:
                                self._m_zero_pad = 1 if self.fc_active else 0
                            return self._m_zero_pad if hasattr(self, '_m_zero_pad') else None

                        @property
                        def state_count(self):
                            """WARNING, it is not exactly `state_count` from `inkwave`, it is divided by 4 (`>>2`) because there it is multiplied by 4, only to `>>8` later (we do `>>6`), but then write into file of other binary format as it is (looks like they have done bit packing in a wrong place, we fix that)
                            !!!WARNING!!!: Read this in each iteration in order to cache it, or you get your stack exceeded
                            """
                            if hasattr(self, '_m_state_count'):
                                return self._m_state_count if hasattr(self, '_m_state_count') else None
                            self._m_state_count = (0 if self.is_first else self._parent.waveform[self.k - 1].state_count) + (0 if self.is_terminator else self.count & 16383)
                            return self._m_state_count if hasattr(self, '_m_state_count') else None

                        @property
                        def should_read_count(self):
                            """if `is_end_of_stream` is `false` and `should_read_count` is `true`, `count_read` still must be read, but it seems it is discarded. Maybe in that case it serves some other purpose."""
                            if hasattr(self, '_m_should_read_count'):
                                return self._m_should_read_count if hasattr(self, '_m_should_read_count') else None
                            self._m_should_read_count = not self.is_end_of_stream and (not self.is_terminator) and (not self.fc_active)
                            return self._m_should_read_count if hasattr(self, '_m_should_read_count') else None

                    class PackedState(KaitaiStruct):

                        def __init__(self, b, _io, _parent=None, _root=None):
                            self._io = _io
                            self._parent = _parent
                            self._root = _root if _root else self
                            self.b = b
                            self._read()

                        def _read(self):
                            pass

                        @property
                        def s0(self):
                            if hasattr(self, '_m_s0'):
                                return self._m_s0 if hasattr(self, '_m_s0') else None
                            self._m_s0 = self.b & 3
                            return self._m_s0 if hasattr(self, '_m_s0') else None

                        @property
                        def s1(self):
                            if hasattr(self, '_m_s1'):
                                return self._m_s1 if hasattr(self, '_m_s1') else None
                            self._m_s1 = self.b >> 2 & 3
                            return self._m_s1 if hasattr(self, '_m_s1') else None

                        @property
                        def s2(self):
                            if hasattr(self, '_m_s2'):
                                return self._m_s2 if hasattr(self, '_m_s2') else None
                            self._m_s2 = self.b >> 4 & 3
                            return self._m_s2 if hasattr(self, '_m_s2') else None

                        @property
                        def s3(self):
                            if hasattr(self, '_m_s3'):
                                return self._m_s3 if hasattr(self, '_m_s3') else None
                            self._m_s3 = self.b >> 6 & 3
                            return self._m_s3 if hasattr(self, '_m_s3') else None

                    @property
                    def state_count(self):
                        if hasattr(self, '_m_state_count'):
                            return self._m_state_count if hasattr(self, '_m_state_count') else None
                        self._m_state_count = self.waveform[len(self.waveform) - 1].state_count
                        return self._m_state_count if hasattr(self, '_m_state_count') else None

                @property
                def wav_addrs(self):
                    if hasattr(self, '_m_wav_addrs'):
                        return self._m_wav_addrs if hasattr(self, '_m_wav_addrs') else None
                    self._m_wav_addrs = self._root.wav_addrs_external
                    return self._m_wav_addrs if hasattr(self, '_m_wav_addrs') else None

                @property
                def waveform(self):
                    if hasattr(self, '_m_waveform'):
                        return self._m_waveform if hasattr(self, '_m_waveform') else None
                    io = self._root._io
                    _pos = io.pos()
                    io.seek(self.wav_addr.ptr)
                    self._raw__m_waveform = io.read_bytes(self.l)
                    _io__raw__m_waveform = KaitaiStream(BytesIO(self._raw__m_waveform))
                    self._m_waveform = EinkWbf.Mode.TempRanges.TempRange.Waveform(_io__raw__m_waveform, self, self._root)
                    io.seek(_pos)
                    return self._m_waveform if hasattr(self, '_m_waveform') else None

                @property
                def cl(self):
                    if hasattr(self, '_m_cl'):
                        return self._m_cl if hasattr(self, '_m_cl') else None
                    _pos = self._io.pos()
                    self._io.seek(0)
                    self._raw__m_cl = self._io.read_bytes(0)
                    _io__raw__m_cl = KaitaiStream(BytesIO(self._raw__m_cl))
                    self._m_cl = EinkWbf.Mode.TempRanges.TempRange.CalcLength(_io__raw__m_cl, self, self._root)
                    self._io.seek(_pos)
                    return self._m_cl if hasattr(self, '_m_cl') else None

                @property
                def l(self):
                    """We are cutting off the last two bytes since we don't know what they are.
                    See section on unsolved mysteries at the top of this file.
                    """
                    if hasattr(self, '_m_l'):
                        return self._m_l if hasattr(self, '_m_l') else None
                    self._m_l = self.cl.size - 2
                    return self._m_l if hasattr(self, '_m_l') else None

        @property
        def ranges(self):
            if hasattr(self, '_m_ranges'):
                return self._m_ranges if hasattr(self, '_m_ranges') else None
            _pos = self._io.pos()
            self._io.seek(self.ptr.ptr)
            self._m_ranges = EinkWbf.Mode.TempRanges(self._io, self, self._root)
            self._io.seek(_pos)
            return self._m_ranges if hasattr(self, '_m_ranges') else None

    class Header(KaitaiStruct):

        class FplPlatform(IntEnum):
            matrix_2_0 = 0
            matrix_2_1 = 1
            matrix_2_3_matrix_vixplex_100 = 2
            matrix_vizplex_110 = 3
            matrix_vizplex_110a = 4
            matrix_vizplex_unknown = 5
            matrix_vizplex_220 = 6
            matrix_vizplex_250 = 7
            matrix_vizplex_220e = 8
            unkn_09 = 9

        class FplSize(IntEnum):
            r_5_0_inch = 0
            r_6_0_inch = 1
            r_6_1_inch = 2
            r_6_3_inch = 3
            r_8_0_inch = 4
            r_9_7_inch = 5
            r_9_9_inch = 6
            r_unknown_07 = 7
            r_5_inch = 50
            r_6_inch_800x600_3c = 60
            r_6_1_inch_1024x768 = 61
            r_6_inch_800x600_3f = 63
            r_8_inch = 80
            r_9_7_inch_1200x825 = 97
            r_9_7_inch_1600x1200 = 99

        class FplRate(IntEnum):
            r_50_hz = 80
            r_60_hz = 96
            r_85_hz = 133

        class RunType(IntEnum):
            baseline = 0
            test_or_trial = 1
            production = 2
            qualification = 3
            v110_a = 4
            v220_c = 5
            d = 6
            v220_e = 7
            f = 8
            g = 9
            h = 10
            i = 11
            j = 12
            k = 13
            l = 14
            m = 15
            n = 16
            unkn_11_likely_o = 17

        class TuningBias(IntEnum):
            standard = 0
            increased_ds_blooming_v110_v110e = 1
            increased_ds_blooming_v220_v220e = 2
            improved_temperature_range = 3
            gc16_fast = 4
            gc16_fast_gl16_fast = 5
            unknown_06 = 6

        class WaveformType(IntEnum):
            wx = 0
            wy = 1
            wp = 2
            wz = 3
            wq = 4
            ta = 5
            wu = 6
            tb = 7
            td = 8
            wv = 9
            wt = 10
            te = 11
            xa = 12
            xb = 13
            we = 14
            wd = 15
            xc = 16
            ve = 17
            xd = 18
            xe = 19
            xf = 20
            wj = 21
            wk = 22
            wl = 23
            vj = 24
            wr = 43
            aa = 60
            ac = 75
            bd = 76
            ae = 80

        class Mode(IntEnum):
            initialization = 0
            direct_update_2 = 1
            grayscale_clearing_16 = 2
            grayscale_clearing_16_fast = 3
            animation2 = 4
            gl16 = 5
            gl16_fast = 6
            direct_update_4 = 7
            reagl = 8
            reagl_dithered = 9
            gl4 = 10
            gl16_inv = 11

        class MfgCode(IntEnum):
            unkn_04 = 4
            unkn_0e = 14
            unkn_30 = 48
            unkn_32 = 50
            ed060scf_v220_6inch_tequila = 51
            ed060scfh1_v220_tequila_hydis_line_2 = 52
            ed060scfh1_v220_tequila_hydis_line_3 = 53
            ed060scfc1_v220_tequila_cmo = 54
            cpt_v220_tequila_cpt = 55
            ed060scg_v220_whitney = 56
            ed060scgh1_v220_whitney_hydis_line_2 = 57
            ed060scgh1_v220_whitney_hydis_line_3 = 58
            ed060scgc1_v220_whitney_cmo = 59
            ed060scgt1_v220_whitney_cpt = 60
            unkn_4d = 77
            unkn_55 = 85
            unkn_59 = 89
            unkn_92 = 146
            unkn_9b = 155
            unknown_lgd_a0 = 160
            unknown_lgd_a1 = 161
            unknown_lgd_a2 = 162
            lb060s03_rd02_lgd_tequila_line_1 = 163
            lgd_tequila_line_2 = 164
            lb060s05_rd02_lgd_whitney_line_1 = 165
            lgd_whitney_line_2 = 166
            unknown_lgd_a7 = 167
            unknown_lgd_a8 = 168
            remarkable_panel = 202
            unkn_db = 219

        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.whole_header_crc32 = self._io.read_u4le()
            self.size = self._io.read_u4le()
            self.serial = self._io.read_u4le()
            self.run_type = KaitaiStream.resolve_enum(EinkWbf.Header.RunType, self._io.read_u1())
            self.fpl_platform = KaitaiStream.resolve_enum(EinkWbf.Header.FplPlatform, self._io.read_u1())
            self.fpl_lot = self._io.read_u2le()
            self.mode_version_or_adhesive_run_num = self._io.read_u1()
            self.waveform_version = self._io.read_u1()
            self.waveform_subversion = self._io.read_u1()
            self.waveform_type = KaitaiStream.resolve_enum(EinkWbf.Header.WaveformType, self._io.read_u1())
            self.fpl_size = KaitaiStream.resolve_enum(EinkWbf.Header.FplSize, self._io.read_u1())
            self.mfg_code = KaitaiStream.resolve_enum(EinkWbf.Header.MfgCode, self._io.read_u1())
            if self.waveform_type >= EinkWbf.Header.WaveformType.wr:
                self.waveform_revision = self._io.read_u1()
            if self.waveform_type <= EinkWbf.Header.WaveformType.wj:
                self.waveform_tuning_bias = KaitaiStream.resolve_enum(EinkWbf.Header.TuningBias, self._io.read_u1())
            if EinkWbf.Header.WaveformType.wj < self.waveform_type and self.waveform_type < EinkWbf.Header.WaveformType.wr:
                self.waveform_tuning_bias_or_rev_or_unkn = self._io.read_u1()
            self.fpl_rate_bcd = bcd.Bcd(2, 4, False, self._io)
            self.fpl_rate = self._io.read_u1()
            self.vcom_shifted = self._io.read_u1()
            self.unknown1 = self._io.read_u2le()
            self.xwia = self._io.read_bits_int_le(24)
            self._io.align_to_byte()
            self.checksum_7_30 = self._io.read_u1()
            _ = self.checksum_7_30
            if not _ == self.checksummer_7_30.calculated_checksum:
                raise kaitaistruct.ValidationExprError(self.checksum_7_30, self._io, u'/types/header/seq/20')
            self.waveform_modes_table = self._io.read_bits_int_le(24)
            self._io.align_to_byte()
            self.fvsn = self._io.read_u1()
            self.luts = self._io.read_u1()
            self.mode_count = self._io.read_u1()
            self.temperature_range_count = self._io.read_u1()
            self.advanced_wfm_flags = self._io.read_u1()
            self.eb = self._io.read_u1()
            self.sb = self._io.read_u1()
            self.reserved_or_unkn = self._io.read_bytes(5)
            self.cs2 = self._io.read_u1()

        class AdvancedWfmFlags(KaitaiStruct):

            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._read()

            def _read(self):
                self.voltage_control = self._io.read_bits_int_le(1) != 0
                self.algorithm_control = self._io.read_bits_int_le(1) != 0
                self.unkn = self._io.read_bits_int_le(6)

        @property
        def another_checksum_method(self):
            """From the kernel it looks like sometimes `size` (header->`filesize`) can be zero. If this is the case there is a different method for calculating the checksum.
            Look at `eink_get_computed_waveform_checksum` in `eink_waveform.c`.
            """
            if hasattr(self, '_m_another_checksum_method'):
                return self._m_another_checksum_method if hasattr(self, '_m_another_checksum_method') else None
            self._m_another_checksum_method = self.size == 0
            return self._m_another_checksum_method if hasattr(self, '_m_another_checksum_method') else None

        @property
        def checksummer_7_30(self):
            if hasattr(self, '_m_checksummer_7_30'):
                return self._m_checksummer_7_30 if hasattr(self, '_m_checksummer_7_30') else None
            _pos = self._io.pos()
            self._io.seek(7)
            self._raw__m_checksummer_7_30 = self._io.read_bytes(23)
            _io__raw__m_checksummer_7_30 = KaitaiStream(BytesIO(self._raw__m_checksummer_7_30))
            self._m_checksummer_7_30 = EinkWbf.Checksummer(0, _io__raw__m_checksummer_7_30, self, self._root)
            self._io.seek(_pos)
            return self._m_checksummer_7_30 if hasattr(self, '_m_checksummer_7_30') else None

        @property
        def bits_per_pixel(self):
            """Dumping `wrf` for waveforms using 5 bits per pixel not yet supported in `inkwave`. Parsing, though, seems to be working."""
            if hasattr(self, '_m_bits_per_pixel'):
                return self._m_bits_per_pixel if hasattr(self, '_m_bits_per_pixel') else None
            self._m_bits_per_pixel = 5 if self.luts & 12 == 4 else 4
            return self._m_bits_per_pixel if hasattr(self, '_m_bits_per_pixel') else None

    class Passthrough(KaitaiStruct):
        """a workaround for missingness of validation in `instance`s."""

        def __init__(self, value, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.value = value
            self._read()

        def _read(self):
            pass

    class Checksummer(KaitaiStruct):
        """A checksummer type.
        """

        def __init__(self, init_value, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.init_value = init_value
            self._read()

        def _read(self):
            self.checksum_calculation = []
            i = 0
            while not self._io.is_eof():
                self.checksum_calculation.append(EinkWbf.Checksummer.Checksum(i, self._io, self, self._root))
                i += 1

        class Checksum(KaitaiStruct):

            def __init__(self, idx, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self.idx = idx
                self._read()

            def _read(self):
                self.ch = self._io.read_u1()

            @property
            def is_first(self):
                if hasattr(self, '_m_is_first'):
                    return self._m_is_first if hasattr(self, '_m_is_first') else None
                self._m_is_first = self.idx == 0
                return self._m_is_first if hasattr(self, '_m_is_first') else None

            @property
            def checksum(self):
                if hasattr(self, '_m_checksum'):
                    return self._m_checksum if hasattr(self, '_m_checksum') else None
                self._m_checksum = (self._parent.init_value if self.is_first else self._parent.checksum_calculation[self.idx - 1].checksum) + self.ch & 255
                return self._m_checksum if hasattr(self, '_m_checksum') else None

        @property
        def calculated_checksum(self):
            if hasattr(self, '_m_calculated_checksum'):
                return self._m_calculated_checksum if hasattr(self, '_m_calculated_checksum') else None
            self._m_calculated_checksum = self.checksum_calculation[len(self.checksum_calculation) - 1].checksum
            return self._m_calculated_checksum if hasattr(self, '_m_calculated_checksum') else None

    class Xwia(KaitaiStruct):

        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.len = self._io.read_u1()
            self._raw_checksummed = self._io.read_bytes(self.len)
            _io__raw_checksummed = KaitaiStream(BytesIO(self._raw_checksummed))
            self.checksummed = EinkWbf.Checksummer(self.len, _io__raw_checksummed, self, self._root)
            self.checksum = self._io.read_u1()
            _ = self.checksum
            if not _ == self.checksummed.calculated_checksum:
                raise kaitaistruct.ValidationExprError(self.checksum, self._io, u'/types/xwia/seq/2')

        @property
        def value(self):
            if hasattr(self, '_m_value'):
                return self._m_value if hasattr(self, '_m_value') else None
            io = self.checksummed._io
            _pos = io.pos()
            io.seek(0)
            self._m_value = io.read_bytes_full().decode(u'ascii')
            io.seek(_pos)
            return self._m_value if hasattr(self, '_m_value') else None

    @property
    def mysterious_offset(self):
        """All mode pointers in the `.wrf` file need to be offset by 63 bytes. Likely has something to do with how they are passed by the epdc kernel module to the epdc."""
        if hasattr(self, '_m_mysterious_offset'):
            return self._m_mysterious_offset if hasattr(self, '_m_mysterious_offset') else None
        self._m_mysterious_offset = 63
        return self._m_mysterious_offset if hasattr(self, '_m_mysterious_offset') else None

    @property
    def xwia(self):
        if hasattr(self, '_m_xwia'):
            return self._m_xwia if hasattr(self, '_m_xwia') else None
        _pos = self._io.pos()
        self._io.seek(self.header.xwia)
        self._m_xwia = EinkWbf.Xwia(self._io, self, self._root)
        self._io.seek(_pos)
        return self._m_xwia if hasattr(self, '_m_xwia') else None

    @property
    def modes(self):
        if hasattr(self, '_m_modes'):
            return self._m_modes if hasattr(self, '_m_modes') else None
        _pos = self._io.pos()
        self._io.seek(self.header.waveform_modes_table)
        self._m_modes = [None] * (self._root.header.mode_count + 1)
        for i in range(self._root.header.mode_count + 1):
            self._m_modes[i] = EinkWbf.Mode(self._io, self, self._root)
        self._io.seek(_pos)
        return self._m_modes if hasattr(self, '_m_modes') else None

    @property
    def wav_addrs_external(self):
        """`calc_length` needs an array of pointers to correctly determine lengths of waveforms."""
        if hasattr(self, '_m_wav_addrs_external'):
            return self._m_wav_addrs_external if hasattr(self, '_m_wav_addrs_external') else None
        _pos = self._io.pos()
        self._io.seek(0)
        self._m_wav_addrs_external = eink_wbf_wav_addrs_collection.EinkWbfWavAddrsCollection(self._root, self._io)
        self._io.seek(_pos)
        return self._m_wav_addrs_external if hasattr(self, '_m_wav_addrs_external') else None
