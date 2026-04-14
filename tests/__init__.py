import os
import sys
import tempfile

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any, List

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
