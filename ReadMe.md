inkwave.py
==========
[wheel (GHA via `nightly.link`)](https://nightly.link/KOLANICH-tools/inkwave.py/workflows/CI/master/inkwave-0.CI-py3-none-any.whl)
[![GitHub Actions](https://github.com/KOLANICH-tools/inkwave.py/workflows/CI/badge.svg)](https://github.com/KOLANICH-tools/inkwave.py/actions/)
[![Libraries.io Status](https://img.shields.io/librariesio/github/KOLANICH-tools/inkwave.py.svg)](https://libraries.io/github/KOLANICH-tools/inkwave.py)
[![Code style: antiflash](https://img.shields.io/badge/code%20style-antiflash-FFF.svg)](https://codeberg.org/KOLANICH-tools/antiflash.py)

This is my rewrite of [`inkwave`](https://github.com/fread-ink/inkwave) into Python in order make it easier for me to create and debug a [Kaitai Struct spec](https://codeberg.org/KOLANICH-specs/kaitai_struct_formats/blob/eink_wbf/hardware/eink_wbf.ksy) for `wbf` format.

[`inkwave`](https://github.com/fread-ink/inkwave) is a command-line utility for converting `.wbf` to `.wrf` files and displaying meta-data information from `.wbf` and `.wrf` files in a human readable format. See its README for more details.

Limitations of the original `inkwave` not necessarily (but are likely) apply to this implementation. And limitations of this impl are not necessarily apply to the original `inkwave`.

Structure of the repo
---------------------

The repo has 2 branches:

* `master` contains the code based on [my spec](https://codeberg.org/KOLANICH-specs/kaitai_struct_formats/blob/eink_wbf/hardware/eink_wbf.ksy) in [Kaitai Struct](https://github.com/kaitai-io/kaitai_struct) language.
* `ported` contains `inkwave` code manually rewritten from C into Python. It works much faster and with less overhead than the code based on a pure KS-based spec.


Copyrigths, licenses, trademarks and disclaimers
-------------------------------------------------

The original `inkwave` software is licensed under GNU [GPL-2.0-only](./COPYING.md). It is a [**viral** license](https://en.wikipedia.org/wiki/Viral_license).

So I am prescribed to license this port under the same license. I would be happy to relicense all of my original contributions to this spec under Unlicense, but it would be illegal without consent of other copyright holders. Licensing this software under GPL is not meant to be interpreted as my approval of so called "intellectual property" system, that must be abolished.

Reversing this format from scratch would have allowed me to use any license I want, but it is orders of magnitude more work, I preferred to rely on an existing working implementation in order to make creating this spec more feasible for me.

Anyway, not all the files of this repo are under GPL. To describe which file has which license we use [Debian machine-readable copyright file](https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/) and [`reuse` tool](https://github.com/fsfe/reuse-tool).

See [the `dep5` file](./.reuse/dep5) for the info on:

* which files are copyrighted by whom and licensed under which licenses;
* disclaimers ot trademarks and affiliations. The disclaimers have been taken from [`inkwave` repo](https://github.com/fread-ink/inkwave), but the wording was modified to match this repo too.


Building
--------
* obtain and install [`kaitaiStructCompile.py`](https://codeberg.org/kaitaiStructCompile/kaitaiStructCompile.py) with `patch` extra.
* build a wheel: `python3 -m build -nwx`. `kaitaiStructCompile` would deals with the rest automatically. It itself would compile the spec into `ksy`, apply the patches and fix the enums.

Limitations and unsolved mysteries
----------------------------------
* https://github.com/kaitai-io/kaitai_struct/issues/815 . Overcome by `fixEnums` postprocessor.
* The spec is currently not expressed entirely in KS, as the original code takes 2 passes, the first pass creates the state (`wav_addrs` array, you must pass it to `eink_wbf::temp_range` as a param of type `eink_wbf_wav_addrs_collection` (see the python file for the example of its impl)) used by the second pass. I don't beleive the format was really designed like that and I feel like it can be possible to get rid of the first pass and express the format entirely in KS, but it has not yet been done.
* The code within `inkwave` looks unnecessary complex, and this complexity has been transfered to this spec. I feel like it can be simplified a lot, but it has not yet been done.
* `bits_per_pixel`
* `mysterious_offset`
* structure of `advanced_wfm_flags` is unknown
* Each waveform segment (WUT?) ends with two bytes that do not appear to be part of the waveform itself. The first is always `0xff` and the second is unpredictable. Unfortunately `0xff` can occur inside of waveforms as well so it is not useful as an endpoint marker. The last byte might be a sort of checksum but does not appear to be a simple 1-byte sum like other 1-byte checksums used in .wbf files.

# Testing
In order to test this implementation (as a part of testing Kaitai-based `inkwave` impl) one needs

* obtain test files and put them into `./test_files`. The files can be

    * downloaded from the Internet (i. e. https://openinkpot.org/pub/contrib/n516-waveforms/default.wbf )
    * extracted from devices firmwares (https://github.com/ReFirmLabs/binwalk is extremily helpful for that, so are the other more specialized tools. If there is no explicit file in the unpacked dir structure, it is likely that blobs of `wbf` format are stored in the firmware for that device. It may be likely that `rkf` format is used.
    * dumped from chips using https://github.com/julbouln/ice40_eink_controller/tree/master/utils/wbf_dump

* obtain and compile [modified `inkwave`](https://codeberg.org/KOLANICH-tools/inkwave/tree/private) with additional tracing
* `find ./test_files/ -name "*.wbf" -print0 | parallel -0 ./tests/convert.sh;` - it would generate traces for the KS-based python impl and C one. They must be equal.
* `find ./test_files/ -name "*.wbf_c.txt" -exec ./tests/compare.sh {} \;` - it would compare them and print any discrepancies.

