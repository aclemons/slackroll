import os
import sys
import tempfile

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any, Dict, List, Optional

    from slackroll import SlackwarePackage

PY2 = sys.version_info[0] == 2

if PY2:
    from mock import patch as _patch  # type: ignore
else:
    from unittest.mock import patch as _patch


class FakeStream(object):
    def __init__(self):
        # type: () -> None
        self.messages = []  # type: List[str]

    def write(self, text):
        # type: (str) -> int
        self.messages.append(text)
        return len(text)

    def flush(self):
        # type: () -> None
        return None

    def getvalue(self):
        # type: () -> str
        return "".join(self.messages)


class PersistentList(object):
    def __init__(self, initial=None):
        # type: (Optional[Dict[str, int]]) -> None
        self._data = initial or {}  # type: Dict[str, int]
        self.sync_calls = 0

    def sync(self):
        # type: () -> None
        self.sync_calls += 1

    def __contains__(self, key):
        # type: (str) -> bool
        return key in self._data

    def __getitem__(self, key):
        # type: (str) -> int
        return self._data[key]

    def __setitem__(self, key, value):
        # type: (str, int) -> None
        self._data[key] = value

    def __delitem__(self, key):
        # type: (str) -> None
        del self._data[key]

    def __iter__(self):
        # type: () -> Any
        return iter(self._data)

    def keys(self):
        # type: () -> List[str]
        return list(self._data.keys())

    def __eq__(self, other):
        # type: (object) -> bool
        return self._data == other


def start_patch(request, target, *args, **kwargs):
    # type: (Any, str, *Any, **Any) -> Any
    patcher = _patch(target, *args, **kwargs)
    mocked = patcher.start()
    request.addfinalizer(patcher.stop)
    return mocked


def named_temporary_file(delete=True):
    # type: (bool) -> Any
    if not PY2:
        return tempfile.NamedTemporaryFile(delete=delete)

    try:
        return tempfile.NamedTemporaryFile(delete=delete)
    except TypeError:
        fd, name = tempfile.mkstemp()

        class _NamedTemporaryFileCompat(object):
            def __init__(self):
                # type: () -> None
                self._file = os.fdopen(fd, "w+b")
                self.name = name
                self._delete = delete

            def write(self, data):
                # type: (bytes) -> Any
                return self._file.write(data)

            def flush(self):
                # type: () -> Any
                return self._file.flush()

            def close(self):
                # type: () -> None
                self._file.close()
                if self._delete and os.path.exists(self.name):
                    os.unlink(self.name)

        return _NamedTemporaryFileCompat()


def bytes_literal(text):
    # type: (str) -> bytes
    if PY2:
        return text
    return text.encode("latin-1")


def decode_bytes_literal(text, encoding):
    # type: (str, str) -> Any
    return bytes_literal(text).decode(encoding)


def persistent_dict(persistent_list):
    # type: (PersistentList) -> Dict[str, int]
    return persistent_list  # type: ignore


def build_pkg(name, version, path):
    # type: (str, str, str) -> SlackwarePackage
    from slackroll import SlackwarePackage

    return SlackwarePackage(name, version, "x86_64", "1", path, ".txz", None, None)


class FakeBinaryBuffer(object):
    def __init__(self):
        # type: () -> None
        self.output = []  # type: List[bytes]

    def write(self, data):
        # type: (bytes) -> None
        self.output.append(data)

    def flush(self):
        # type: () -> None
        return None

    def close(self):
        # type: () -> None
        return None


class FakeStdout(object):
    def __init__(self):
        # type: () -> None
        self.buffer = FakeBinaryBuffer()
        self.output = []  # type: List[str]

    def isatty(self):
        # type: () -> bool
        return False

    def write(self, data):
        # type: (str) -> None
        self.output.append(data)

    def flush(self):
        # type: () -> None
        return None


class FakeTtyStdout(FakeStdout):
    def isatty(self):
        # type: () -> bool
        return True


class FakePager(object):
    def __init__(self):
        # type: () -> None
        self.stdin = FakeBinaryBuffer()

    def wait(self):
        # type: () -> None
        return None
