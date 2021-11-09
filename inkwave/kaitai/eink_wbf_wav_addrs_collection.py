from kaitaistruct import KaitaiStruct
import typing
from typing import Union

import bisect

def binSearch(arr: list, v: int) -> int:
	if not arr:
		return -1

	b = len(arr) - 1

	if arr[b] < v:
		return b

	if arr[0] >= v:
		return -1

	a = 0

	d = b - a
	m = a
	while d > 1:
		d = b - a
		m = (a + b) // 2
		el = arr[m]
		if el >= v:  # [ a v el b ]
			b = m
		else:
			a = m
	return m


class WaveformTracker:
	__slots__ = ("wAddrs",)

	def __init__(self):
		self.wAddrs = [0]

	def add(self, addr: int):
		# print("Add ", addr)
		idx = binSearch(self.wAddrs[:-1], addr) + 1
		# print(self.wAddrs[idx], "idx", idx, self.wAddrs[:idx], self.wAddrs[idx], self.wAddrs[idx+1:])

		d = self.wAddrs[idx] - addr
		if not d:
			return
		else:
			self.wAddrs.insert(idx, addr)


class EinkWbfWavAddrsCollection(KaitaiStruct):
	def __init__(self, _root, _io=None, _parent=None):
		self._io = _io
		self._parent = _parent
		self._root = _root if _root else self
		self.wt = WaveformTracker()
		self.arr = self.wt.wAddrs

		# add file endpoint to waveform address table
		# since we use this to determine end address of each waveform
		self.wt.add(_io.size())

	class Add(KaitaiStruct):
		def __init__(self, ptr, collection, _io=None, _parent=None):
			collection.wt.add(ptr)
