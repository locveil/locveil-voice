"""AssetManager archive extraction — .tar.bz2 support (ARCH-24 T2 / Piper).

Piper TTS voices ship as k2-fsa `.tar.bz2` archives (model.onnx + tokens.txt + espeak-ng-data/).
`_extract_archive` previously only dispatched .tar/.tar.gz/.tgz (and Path.suffix on `foo.tar.bz2`
is just `.bz2`), so a Piper voice would fail with "Unsupported archive format". These cover the
fix: dispatch by full name + bzip2 header magic, with tarfile's `r:*` doing the decompression.
"""

import asyncio
import tarfile

import pytest

from irene.core.assets import AssetManager

try:
    import bz2  # noqa: F401
    _HAS_BZ2 = True
except ImportError:
    # The dev/CI interpreter (custom-built /usr/local CPython) lacks the bz2 module, like _sqlite3.
    # Real deployment images use python:3.11-slim (Debian, libbz2 present), so this is env-only.
    _HAS_BZ2 = False

needs_bz2 = pytest.mark.skipif(not _HAS_BZ2, reason="interpreter built without the bz2 module (env-only; Docker images have it)")


def _make_targz(path, **members):
    with tarfile.open(path, "w:gz") as t:
        _add(t, members)


def _make_tarbz2(path, **members):
    with tarfile.open(path, "w:bz2") as t:
        _add(t, members)


def _add(t, members):
    import io
    for arcname, data in members.items():
        info = tarfile.TarInfo(arcname)
        info.size = len(data)
        t.addfile(info, io.BytesIO(data))


def _extract(tmp_path, archive, url):
    am = object.__new__(AssetManager)  # _extract_archive uses no instance state
    target = tmp_path / "out"
    asyncio.run(am._extract_archive(archive, target, model_url=url))
    return target


@needs_bz2
def test_extract_tar_bz2_by_name(tmp_path):
    arc = tmp_path / "vits-piper-ru_RU-irina-medium.tar.bz2"
    _make_tarbz2(arc, **{"voice/model.onnx": b"onnx", "voice/tokens.txt": b"tok",
                         "voice/espeak-ng-data/ru_dict": b"d"})
    out = _extract(tmp_path, arc, url="https://example/vits-piper-ru_RU-irina-medium.tar.bz2")
    assert (out / "voice" / "model.onnx").read_bytes() == b"onnx"
    assert (out / "voice" / "espeak-ng-data" / "ru_dict").exists()


@needs_bz2
def test_extract_tar_bz2_by_header_when_url_unknown(tmp_path):
    # No tell-tale URL/extension → must fall back to the bzip2 (BZh) header magic.
    arc = tmp_path / "voice.bin"
    _make_tarbz2(arc, **{"model.onnx": b"x"})
    out = _extract(tmp_path, arc, url=None)
    assert (out / "model.onnx").read_bytes() == b"x"


def test_extract_tar_gz_still_works(tmp_path):
    arc = tmp_path / "pack.tar.gz"
    _make_targz(arc, **{"a.txt": b"a"})
    out = _extract(tmp_path, arc, url="https://example/pack.tar.gz")
    assert (out / "a.txt").read_bytes() == b"a"
