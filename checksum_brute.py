from inkwave.kaitai.eink_wbf import EinkWbf
from pathlib import Path
from zlib import crc32
from itertools import accumulate


def bruteChecksum(s, csTarget):
	validLocs = set()
	for i, a in enumerate(s):
		for j, b in enumerate(s[i:]):
			if ((b - a) & 0xFF) == csTarget:
				validLocs.add((i, i + j, j))
	return validLocs


def genCsValidLocs(f):
	d = f.read_bytes()
	w = EinkWbf.from_bytes(d)
	return bruteChecksum(d[:100], w.header.cs2)


if __name__ == "__main__":
	fs = list(Path("./test_files/").glob("*.wbf"))
	print(len(fs))
	fsI = iter(fs)

	valids = genCsValidLocs(next(fsI))
	print(len(valids))

	for f in fsI:
		valids &= genCsValidLocs(f)
		print(len(valids))

	print(len(valids))
	print(sorted(valids))
