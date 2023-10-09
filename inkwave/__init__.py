#!/usr/bin/env python3

import heapq
import io
import mmap
import os
import struct
import sys
import typing
from enum import IntEnum, IntFlag
from io import IOBase
from itertools import takewhile
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Union
from zlib import crc32
from warnings import warn

import kaitaistruct

from .kaitai.eink_wbf import EinkWbf

warn("We have moved from M$ GitHub to https://codeberg.org/KOLANICH-tools/inkwave.py , read why on https://codeberg.org/KOLANICH/Fuck-GuanTEEnomo .")

class uint(int):
	def __init__(self, v: Union[int, "uint"]) -> None:
		self = v


class uint64_t(uint):
	def __init__(self, v: Union[int, "uint64_t"]) -> None:
		super().__init__(v & 0xFFFFFFFFFFFFFFFF)


class uint32_t(uint64_t):
	def __init__(self, v: Union[int, "uint32_t"]) -> None:
		super().__init__(v & 0xFFFFFFFF)


class uint16_t(uint32_t):
	def __init__(self, v: Union[int, "uint16_t"]) -> None:
		super().__init__(v & 0xFFFF)


class uint8_t(uint16_t):
	def __init__(self, v: Union[int, "uint8_t"]) -> None:
		super().__init__(v & 0xFF)


class int64_t(int):
	def __init__(self, v: Union[int, "int64_t"]):
		super().__init__(v & 0xFFFFFFFFFFFFFFFF)


class size_t(uint64_t):
	pass


class int32_t(int64_t):
	def __init__(self, v: Union[int, "int32_t"]):
		super().__init__(v & 0xFFFFFFFF)


class int16_t(int32_t):
	def __init__(self, v: Union[int, "int16_t"]):
		super().__init__(v & 0xFFFF)


class int8_t(int16_t):
	def __init__(self, v: Union[int, "int8_t"]):
		super().__init__(v & 0xFF)


# there probably aren't any displays with more waveforms than this (we hope)
# (technically the header allows for 256 * 256 waveforms but that's not realistic)
MAX_WAVEFORMS = 4096

# these are the actual maximums
MAX_MODES = 256
MAX_TEMP_RANGES = 256

# for unknown reasons addresses in the .wrf file
# need to be offset by 63 bytes
MYSTERIOUS_OFFSET = 63


MODE = EinkWbf.Header.Mode

update_modes = {
	MODE.initialization: "INIT (panel initialization / clear screen to white)",
	MODE.direct_update_2: "DU (direct update, gray to black/white transition, 1bpp)",
	MODE.grayscale_clearing_16: "GC16 (high fidelity, flashing, 4bpp)",
	MODE.grayscale_clearing_16_fast: "GC16_FAST (medium fidelity, 4bpp)",
	MODE.animation2: "A2 (animation update, fastest and lowest fidelity)",
	MODE.gl16: "GL16 (high fidelity from white transition, 4bpp)",
	MODE.gl16_fast: "GL16_FAST (medium fidelity from white transition, 4bpp)",
	MODE.direct_update_4: "DU4 (direct update, medium fidelity, text to text, 2bpp)",
	MODE.reagl: "REAGL (non-flashing, ghost-compensation)",
	MODE.reagl_dithered: "REAGLD (non-flashing, ghost-compensation with dithering)",
	MODE.gl4: "GL4 (2-bit from white transition, 2bpp)",
	MODE.gl16_inv: "GL16_INV (high fidelity for black transition, 4bpp)"
}

mfg_codes = {
	EinkWbf.Header.MfgCode.ed060scf_v220_6inch_tequila: 'ED060SCF (V220 6" Tequila)',
	EinkWbf.Header.MfgCode.ed060scfh1_v220_tequila_hydis_line_2: "ED060SCFH1 (V220 Tequila Hydis – Line 2)",
	EinkWbf.Header.MfgCode.ed060scfh1_v220_tequila_hydis_line_3: "ED060SCFH1 (V220 Tequila Hydis – Line 3)",
	EinkWbf.Header.MfgCode.ed060scfc1_v220_tequila_cmo: "ED060SCFC1 (V220 Tequila CMO)",
	EinkWbf.Header.MfgCode.cpt_v220_tequila_cpt: "ED060SCFT1 (V220 Tequila CPT)",
	EinkWbf.Header.MfgCode.ed060scg_v220_whitney: "ED060SCG (V220 Whitney)",
	EinkWbf.Header.MfgCode.ed060scgh1_v220_whitney_hydis_line_2: "ED060SCGH1 (V220 Whitney Hydis – Line 2)",
	EinkWbf.Header.MfgCode.ed060scgh1_v220_whitney_hydis_line_3: "ED060SCGH1 (V220 Whitney Hydis – Line 3)",
	EinkWbf.Header.MfgCode.ed060scgc1_v220_whitney_cmo: "ED060SCGC1 (V220 Whitney CMO)",
	EinkWbf.Header.MfgCode.ed060scgt1_v220_whitney_cpt: "ED060SCGT1 (V220 Whitney CPT)",
	EinkWbf.Header.MfgCode.unknown_lgd_a0: "Unknown LGD panel",
	EinkWbf.Header.MfgCode.unknown_lgd_a1: "Unknown LGD panel",
	EinkWbf.Header.MfgCode.unknown_lgd_a2: "Unknown LGD panel",
	EinkWbf.Header.MfgCode.lb060s03_rd02_lgd_tequila_line_1: "LB060S03-RD02 (LGD Tequila Line 1)",
	EinkWbf.Header.MfgCode.lgd_tequila_line_2: "2nd LGD Tequila Line",
	EinkWbf.Header.MfgCode.lb060s05_rd02_lgd_whitney_line_1: "LB060S05-RD02 (LGD Whitney Line 1)",
	EinkWbf.Header.MfgCode.lgd_whitney_line_2: "2nd LGD Whitney Line",
	EinkWbf.Header.MfgCode.unknown_lgd_a7: "Unknown LGD panel",
	EinkWbf.Header.MfgCode.unknown_lgd_a8: "Unknown LGD panel",
	EinkWbf.Header.MfgCode.remarkable_panel: "reMarkable panel?",
}

run_types = {
	EinkWbf.Header.RunType.baseline: "[B]aseline",
	EinkWbf.Header.RunType.test_or_trial: "[T]est/trial",
	EinkWbf.Header.RunType.production: "[P]roduction",
	EinkWbf.Header.RunType.qualification: "[Q]ualification",
	EinkWbf.Header.RunType.v110_a: "V110[A]",
	EinkWbf.Header.RunType.v220_c: "V220[C]",
	EinkWbf.Header.RunType.d: "D",
	EinkWbf.Header.RunType.v220_e: "V220[E]",
	EinkWbf.Header.RunType.f: "F",
	EinkWbf.Header.RunType.g: "G",
	EinkWbf.Header.RunType.h: "H",
	EinkWbf.Header.RunType.i: "I",
	EinkWbf.Header.RunType.j: "J",
	EinkWbf.Header.RunType.k: "K",
	EinkWbf.Header.RunType.l: "L",
	EinkWbf.Header.RunType.m: "M",
	EinkWbf.Header.RunType.n: "N"
}

fpl_platforms = {
	EinkWbf.Header.FplPlatform.matrix_2_0: "Matrix 2.0",
	EinkWbf.Header.FplPlatform.matrix_2_1: "Matrix 2.1",
	EinkWbf.Header.FplPlatform.matrix_2_3_matrix_vixplex_100: "Matrix 2.3 / Matrix Vixplex (V100)",
	EinkWbf.Header.FplPlatform.matrix_vizplex_110: "Matrix Vizplex 110 (V110)",
	EinkWbf.Header.FplPlatform.matrix_vizplex_110a: "Matrix Vizplex 110A (V110A)",
	EinkWbf.Header.FplPlatform.matrix_vizplex_unknown: "Matrix Vizplex unknown",
	EinkWbf.Header.FplPlatform.matrix_vizplex_220: "Matrix Vizplex 220 (V220)",
	EinkWbf.Header.FplPlatform.matrix_vizplex_250: "Matrix Vizplex 250 (V250)",
	EinkWbf.Header.FplPlatform.matrix_vizplex_220e: "Matrix Vizplex 220E (V220E)"
}

fpl_sizes = {
	EinkWbf.Header.FplSize.r_5_0_inch: '5.0"',
	EinkWbf.Header.FplSize.r_6_0_inch: '6.0"',
	EinkWbf.Header.FplSize.r_6_1_inch: '6.1"',
	EinkWbf.Header.FplSize.r_6_3_inch: '6.3"',
	EinkWbf.Header.FplSize.r_8_0_inch: '8.0"',
	EinkWbf.Header.FplSize.r_9_7_inch: '9.7"',
	EinkWbf.Header.FplSize.r_9_9_inch: '9.9"',
	EinkWbf.Header.FplSize.r_unknown_07: "Unknown",
	EinkWbf.Header.FplSize.r_5_inch: '5", unknown resolution',
	EinkWbf.Header.FplSize.r_6_inch_800x600_3c: '6", 800x600',
	EinkWbf.Header.FplSize.r_6_1_inch_1024x768: '6.1", 1024x768',
	EinkWbf.Header.FplSize.r_6_inch_800x600_3f: '6", 800x600',
	EinkWbf.Header.FplSize.r_8_inch: '8", unknown resolution',
	EinkWbf.Header.FplSize.r_9_7_inch_1200x825: '9.7", 1200x825',
	EinkWbf.Header.FplSize.r_9_7_inch_1600x1200: '9.7", 1600x1200',
}

mode_versions = {
	0x00: "MU/GU/GC/PU (V100 modes)",
	0x01: "DU/GC16/GC4 (V110/V110A modes)",
	0x02: "DU/GC16/GC4 (V110/V110A modes)",
	0x03: "DU/GC16/GC4/AU (V220, 50Hz/85Hz modes)",
	0x04: "DU/GC16/AU (V220, 85Hz modes)",
	0x06: "? (V220: 210 dpi: 85Hz modes)",
	0x07: "? (V220, 210 dpi, 85Hz modes)",
}

waveform_tuning_biases = {
	EinkWbf.Header.TuningBias.standard: "Standard",
	EinkWbf.Header.TuningBias.increased_ds_blooming_v110_v110e: "Increased DS Blooming V110/V110E",
	EinkWbf.Header.TuningBias.increased_ds_blooming_v220_v220e: "Increased DS Blooming V220/V220E",
	EinkWbf.Header.TuningBias.improved_temperature_range: "Improved temperature range",
	EinkWbf.Header.TuningBias.gc16_fast: "GC16 fast",
	EinkWbf.Header.TuningBias.gc16_fast_gl16_fast: "GC16 fast, GL16 fast",
	EinkWbf.Header.TuningBias.unknown_06: "Unknown",
}


def get_desc(table: Mapping[int, str], key: int, default: str) -> str:
	if key in table:
		return table[key]

	if default:
		return default

	return "Unknown"


def print_modes(mode_count: uint8_t) -> None:
	i: uint8_t = 0
	desc: str = ""

	print("Modes in file:")
	for i in range(0, mode_count):
		i = MODE(i)
		desc = get_desc(update_modes, i, "Unknown mode")
		print("	{:2d}: {}".format(i, desc))

	print("")


def get_desc_mfg_code(mfg_code: uint) -> str:
	desc: str = get_desc(mfg_codes, mfg_code, "")

	if desc:
		return desc

	if mfg_code >= 0x33 and mfg_code < 0x3C:
		return "PVI/EIH panel\0"

	if mfg_code >= 0xA0 and mfg_code < 0xA8:
		return "LGD panel\0"

	return "Unknown code\0"


class waveform_data_header:
	__slots__ = ("ks",)
	structStr = "IIIBBHBBBBBBBBBBHHBBHBBBBBBBBBBBBBB"
	parser = struct.Struct(structStr)
	structSize = struct.calcsize(structStr)

	def __getattr__(self, k: str):
		return getattr(self.ks, k)

	def __init__(self, ks: EinkWbf.Header) -> None:
		self.__class__.ks.__set__(self, ks)

	def __bytes__(self):
		return self.__class__.parser.pack((self.whole_header_crc32, self.size, self.serial, self.run_type, self.fpl_platform, self.fpl_lot, self.mode_version_or_adhesive_run_num, self.waveform_version, self.waveform_subversion, self.waveform_type, self.fpl_size, self.mfg_code, self.waveform_tuning_bias_or_rev, self.fpl_rate_bcd, self.unknown0, self.vcom_shifted, self.unknown1, self.xwia.lo, self.xwia.hi, self.checksum_7_30, self.waveform_modes_table.lo, self.waveform_modes_table.hi, self.fvsn, self.luts, self.mode_count, self.temperature_range_count, self.advanced_wfm_flags, self.eb, self.sb, self.reserved_or_unkn, self.reserved0_2, self.reserved0_3, self.reserved0_4, self.reserved0_5, self.cs2))


def temp_range(data: bytes):
	"""
	struct temp_range {
		uint8_t from;
		uint8_t to;
	};"""
	return range(*struct.unpack("HBB", data))

CRC32_START_VALUE = 0x2144DF1C  # crc32(b"\0\0\0\0")


def compare_checksum(data: str, header: waveform_data_header) -> int:
	if crc32(data[4 : header.size], CRC32_START_VALUE) != header.whole_header_crc32:
		return -1
	return 0


def add_addr(addrs: typing.List[uint32_t], addr: uint32_t) -> int:
	# ToDo: replace with a heap
	i = 0  # type: uint32_t

	for i in range(len(addrs)):
		if addrs[i] == addr:
			return 0
			# this address was already in the array
		if not addrs[i]:
			addrs[i] = addr
			return 1  # added

	print("Encountered more addresses than our hardcoded max", file=sys.stderr)
	return -1


def print_header(header: waveform_data_header, is_wbf: int) -> None:
	print("Header info:")
	if is_wbf:
		print("	File size (according to header): " + str(header.size) + " bytes")
	print("	Serial number: " + str(header.serial))
	print("	Run type: " + hex(header.run_type) + " | " + get_desc(run_types, header.run_type, "Unknown"))
	print("	Manufacturer code: " + hex(header.mfg_code) + " | " + get_desc_mfg_code(header.mfg_code))

	print("	Frontplane Laminate (FPL) platform: " + hex(header.fpl_platform) + " | " + get_desc(fpl_platforms, header.fpl_platform, "Unknown"))
	print("	Frontplane Laminate (FPL) lot: " + str(header.fpl_lot))
	print("	Frontplane Laminate (FPL) size: " + hex(header.fpl_size) + " | " + get_desc(fpl_sizes, header.fpl_size, "Unknown"))
	print("	Frontplane Laminate (FPL) rate: " + hex(header.fpl_rate_bcd.digits[0]) + hex(header.fpl_rate_bcd.digits[1])[2:] + " | " + str(header.fpl_rate_bcd.as_int) + "Hz")

	print("	Waveform version: " + str(header.waveform_version))
	print("	Waveform sub-version: " + str(header.waveform_subversion))

	if isinstance(header.waveform_type, EinkWbf.Header.WaveformType):
		waveform_type_text_repr = header.waveform_type.name.upper()
	else:
		waveform_type_text_repr = "Unknown"

	print("	Waveform type: " + hex(header.waveform_type) + " | " + waveform_type_text_repr)

	try:  # WJ type or earlier
		print("	Waveform tuning bias: " + hex(header.waveform_tuning_bias) + " | " + get_desc(waveform_tuning_biases, header.waveform_tuning_bias, None))
	except AttributeError:
		print("	Waveform tuning bias: Unknown")

	try:  # WR type or later
		print("	Waveform revision: " + str(header.waveform_revision))
	except AttributeError:
		print("	Waveform revision: Unknown")

	# if fpl_platform is < 3 then
	# mode_version_or_adhesive_run_num is the adhesive run number
	if header.fpl_platform.value < 3:
		print("	Adhesive run number: " + str(header.mode_version_or_adhesive_run_num))
		print("	Mode version: Unknown")
	else:
		print("	Adhesive run number: Unknown")
		print("	Mode version: " + hex(header.mode_version_or_adhesive_run_num) + " | " + get_desc(mode_versions, header.mode_version_or_adhesive_run_num, None))

	print("	Number of modes in this waveform: " + str(header.mode_count + 1))
	print("	Number of temperature ranges in this waveform: " + str(header.temperature_range_count + 1))

	print("	4 or 5-bits per pixel: " + str(header.bits_per_pixel))

	print("	unknown0: " + hex(header.fpl_rate))
	print("	vcom_shifted: " + str(header.vcom_shifted))
	print("	extra waveform info (xwia) offset: " + hex(header.xwia))
	
	print("	cs1: " + hex(header.checksum_7_30))
	print("	waveform modes table offset: " + hex(header.waveform_modes_table))
	print("	fvsn: " + hex(header.fvsn))
	print("	luts: " + hex(header.luts))
	print("	advanced_wfm_flags: " + hex(header.advanced_wfm_flags))
	print("	eb: " + hex(header.eb))
	print("	sb: " + hex(header.sb))
	if any(header.reserved_or_unkn):
		print("	reserved_or_unkn: " + " ".join((hex(el)[2:] for el in header.reserved_or_unkn)))
	print("	cs2: " + hex(header.cs2))

	print("")


def toS(n: int):
	if n & 0x80:
		return n - 0x80

	return n


def dump_waveform(wf: "EinkWbf.EinkWbfWaveform", outfile: io.IOBase):
	for el in wf.waveform.waveform:
		#print("{}, {}".format(i, hex(el.current_byte)[2:]))
		if not el.is_terminator:
			el.state_count  # HAS SIDE EFFECTS! DON"T REMOVE!

			if outfile:
				for j in range(count):
					outfile.write(struct.pack("BBBB", el.s.s0, el.s.s1, el.s.s2, el.s.s3))

def parse_temp_ranges(header: waveform_data_header, data: str, ranges: "EinkWbf.TempRanges", outfile: io.IOBase, do_print: int) -> int:
	tr = None  # type: EinkWbf.ChecksummedPtr
	checksum = 0  # type: uint8_t
	i = 0  # type: uint8_t
	state_count = 0  # type: uint16_t
	written = 0  # type: size_t
	ftable = 0  # type: long
	fprev = 0  # type:: long
	fcur = 0  # type:: long
	tr_addrs = [0] * MAX_TEMP_RANGES  # type: typing.List[uint32_t]
	# temperature range addresses for output file
	tr_table_addr = 0  # type: uint32_t
	# temperature range table output start address

	# memset(tr_addrs, 0, sizeof(tr_addrs))

	if do_print:
		print("		Temperature ranges: ")

	if outfile:
		ftable = outfile.tell()

		outfile.seek((header.temperature_range_count + 1) * 8, SEEK_CUR)

	for i, rangeFull in enumerate(ranges.ranges):
		if do_print:
			sys.stdout.write("			Checking range {:2d}: ".format(i))

		if outfile:

			fprev = outfile.tell()

			if add_addr(tr_addrs, fprev - MYSTERIOUS_OFFSET) < 0:
				return -1

			outfile.seek(8, SEEK_CUR)

		# TODO
		# We are cutting off the last two bytes
		# since we don't know what they are.
		# See section on unsolved mysteries at the top of this file.
		try:
			kw = rangeFull
			#kw.waveform  # fucking cached
		except kaitaistruct.ValidationExprError as e:
			print("Could not find waveform length", file=stderr)
			return -1

		dump_waveform(kw, outfile)
		state_count = kw.waveform.state_count

		if state_count < 0:
			return -1

		if do_print:
			print("{:4d} phases ({:4d})".format(state_count >> 6, rangeFull.wav_addr.ptr))

		if outfile:
			fcur = outfile.tell()

			outfile.seek(fprev, SEEK_SET)

			# write state count
			written = outfile.write((state_count << 2).pack(">H"))

			outfile.fseek(fcur, SEEK_SET)

	if do_print:
		print("")

	if outfile:
		if write_table(ftable, tr_addrs, outfile, MAX_TEMP_RANGES) < 0:
			print("Error writing temperature range table", file=sys.stderr)
			return -1

	return 0


def parse_modes(header: waveform_data_header, data: str, modes: str, first_pass: int, outfile: io.IOBase, do_print: int) -> int:
	mode = None  # type: EinkWbf.ChecksummedPtr
	checksum = 0  # type: uint8_t
	i = 0  # type: uint8_t
	pos = 0  # type: int
	mode_addrs = [0] * MAX_MODES  # type: typing.List[uint32_t] = [0] * 256
	# mode addresses for output file
	mode_table_addr = 0  # type: uint32_t
	# mode table output start address

	# memset(mode_addrs, 0, sizeof(mode_addrs))

	if do_print:
		print("Modes: ")

	#print(modes, file=sys.stderr)

	for i, modeFull in enumerate(modes):
		ranges = modeFull.ranges

		if do_print:
			sys.stdout.write("	Checking mode {:2d}: ".format(i))

		if outfile:

			pos = outfile.tell() - MYSTERIOUS_OFFSET

			if add_addr(mode_addrs, pos) < 0:
				return -1

		if do_print:
			print("Passed")

		if not first_pass:
			if parse_temp_ranges(header, data, ranges, outfile, do_print) < 0:
				return -1

	if outfile:
		# the + 2 is because there is one more temperature range than the
		# count in header.temperature_range_count and then because these are ranges there is one
		# more temperature than the number of ranges
		mode_table_addr = waveform_data_header.structSize + header.temperature_range_count + 2

		if write_table(mode_table_addr, mode_addrs, outfile, MAX_MODES) < 0:
			print("Error writing mode table", file=sys.stderr)
			return -1

	return 0


def print_xwia(xwia: EinkWbf.Xwia):
	i = 0  # type: uint8_t
	non_printables = 0  # type: int

	xwia_s = xwia.value

	for i in range(0, len(xwia_s)):
		if not xwia_s[i].isprintable():
			non_printables += 1

	sys.stdout.write("Extra Waveform Info (probably waveform's original filename): ")

	if not xwia.len:
		print("None")
	elif non_printables:
		print("(" + str(xwia.len) + " bytes containing " + str(non_printables) + " unprintable characters)")
	else:
		print(xwia_s)

	print("")


def dump_temp_range_table(temp_range_table: EinkWbf.TempRangeTable, outfile: io.IOBase, do_print: int) -> int:
	i = 0  # type: uint8_t
	written = 0  # type: size_t

	if not len(temp_range_table.ranges):
		return 0

	if do_print:
		print("Supported temperature ranges:")

	for rng in temp_range_table.ranges:
		if do_print:
			print("	" + str(rng.start) + " - " + str(rng.stop) + " °C")

	if outfile:
		written = outfile.fwrite(table, 1, len(temp_range_table.ranges))
		if written != len(temp_range_table.ranges):
			print("Error writing temperature range table to output file: " + strerror(errno) + "\n", file=sys.stderr)
			return -1

	if do_print:
		print("")

	return 0


def write_table(table_addr: uint32_t, addrs: typing.List[uint32_t], outfile: io.IOBase, max: uint32_t) -> int:
	i = 0  # type: int
	written = 0  # type: size_t
	addr = 0  # type: uint32_t
	prev = 0  # type: int

	prev = outfile.tell()
	if prev < 0:
		return -1

	outfile.seek(table_addr, SEEK_SET)

	for i in range(0, max):
		if not addrs[i]:
			break

		addr = addrs[i]

		written = outfile.fwrite(struct.pack("I", addr))
		if written != struct.calcsize("I"):
			print("Error writing address table to output file: " + strerror(errno) + "\n", file=sys.stderr)
			return -1

		outfile.seek(4, SEEK_CUR)

	outfile.seek(prev, SEEK_SET)

	return 0


def write_header(outfile: io.IOBase, header: waveform_data_header) -> int:
	written = 0  # type: size_t

	written = outfile.write(header.serialize())
	if written < waveform_data_header.structSize:
		return -1

	return 0



def mainAPI(infile_path: Path, force_input: bool, outfile_path: Optional[Path], do_print: int = 0) -> int:
	infile_path = Path(infile_path)  # type: Path
	infile = None  # type: io.IOBase
	header = None  # type: waveform_data_header
	# points to `data` at beginning of header
	modes = None  # type: str
	# points to `data` where the modes table begins
	temp_range_table = None  # type: str
	# points to `data` where the temp range table begins
	xwia_len = 0  # type: uint32_t
	mode_count = 0  # type: uint8_t
	temp_range_count = 0  # type: uint8_t
	outfile = None  # type: io.IOBase
	force_input = force_input  # type: str
	force = 0  # type: int
	c = 0  # type: int
	unique_waveform_count = None  # type: uint32_t
	# waveform addresses in input file
	is_wbf = 0  # type: uint32_t
	to_alloc = 0  # type: size_t

	if outfile_path:
		outfile_path = Path(outfile_path)

	# memset(wav_addrs, 0, sizeof(wav_addrs))

	# try:
	if force_input:
		if force_input == "wbf":
			is_wbf = 1
		elif force_input == "wrf":
			is_wbf = 0
		else:
			print("Only wbf and wrf format is supported", file=sys.stderr)
			raise Exception
	else:
		if not infile_path.suffix:
			print("File has neither .wbf or .wrf extension", file=sys.stderr)
			print("Consider using `-f` to bypass file format detection", file=sys.stderr)
			raise Exception
		if infile_path.suffix == ".wbf":
			is_wbf = 1
		elif infile_path.suffix == ".wrf":
			is_wbf = 0
		else:
			print("File has neither .wbf or .wrf extension", file=sys.stderr)
			print("Consider using `-f` to bypass file format detection", file=sys.stderr)
			raise Exception

	if not is_wbf and outfile_path:
		print("Conversion from .wrf format not supported", file=sys.stderr)
		raise Exception

	with infile_path.open("rb") as infile:
		st = infile_path.stat()

		if is_wbf:
			to_alloc = st.st_size
		else:
			to_alloc = waveform_data_header.structSize

		with mmap.mmap(infile.fileno(), to_alloc, access=mmap.ACCESS_READ) as data:

			if outfile_path:
				outfile = outfile_path.open("wb")

			if not do_print and not outfile:
				do_print = 1

			if do_print:
				print("")
				print("File size: " + str(st.st_size) + " bytes")
				print("")

			parsed = EinkWbf(kaitaistruct.KaitaiStream(data))
			if do_print == 2:
				parsed.debug = True

			header = waveform_data_header(parsed.header)

			if is_wbf:
				if header.size != st.st_size:
					print("Actual file size does not match file size reported by waveform header", file=sys.stderr)
					raise Exception

			if outfile:
				if header.bits_per_pixel != 4:
					print("This waveform uses 5 bits per pixel which is not yet support", file=sys.stderr)
					raise Exception

			if is_wbf:
				if compare_checksum(data, header) < 0:
					print("Checksum error", file=sys.stderr)
					raise Exception

			if do_print:
				print_header(header, is_wbf)

				if header.fpl_platform.value < 3:
					print("Modes: Unknown (no mode version specified)")
				else:
					print_modes(header.mode_count + 1)

			if not is_wbf:
				return 0

			if outfile:
				if write_header(outfile, header) < 0:
					print("Writing header to output failed", file=sys.stderr)
					raise Exception

			# start of temperature range table
			temp_range_table = None
			try:
				temp_range_table = parsed.temp_range_table
			except kaitaistruct.ValidationExprError:
				print("Temperature range checksum error", file=sys.stderr)
				raise
			else:
				dump_temp_range_table(temp_range_table, outfile, do_print)

			if outfile:
				outfile.seek(8 * (header.mode_count + 1), SEEK_CUR)

			try:
				parsed_xwia = parsed.xwia
			except kaitaistruct.ValidationExprError:
				print("xwia checksum error", file=sys.stderr)
				raise
			else:
				if do_print:
					print_xwia(parsed_xwia)

			try:
				modes = parsed.modes
			except kaitaistruct.ValidationExprError as e:
				print(e, file=sys.stderr)
				if do_print:
					print("Failed")
				return -1
			else:
				unique_waveform_count = 0
				for wfa in parsed.wav_addrs_external.arr:
					if not wfa:
						break
					unique_waveform_count += 1

				unique_waveform_count -= 1 # we have already added file size

				# already sorted
				#wav_addrs_uniq = parsed.wav_addrs_external.arr[:unique_waveform_count]
				#wav_addrs_uniq.sort()
				#del wav_addrs_uniq

				if do_print:
					print("Number of unique waveforms: " + str(unique_waveform_count) + "\n")

				# parse modes again since we now have all the sorted waveform addresses
				if parse_modes(header, data, modes, 0, outfile, do_print) < 0:
					print("Parse error during second pass", file=sys.stderr)
					raise Exception

			return 0

	# finally:
	# 	outfile.__exit__()
	return 1


if __name__ == "__main__":
	MainCLI.run()
