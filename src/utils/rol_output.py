import ctypes
import os
import sys
import tempfile
from pathlib import Path
from typing import Iterable, Union


def capture_stream_output(func):
    """Capture stdout/stderr emitted by ``func`` and return it as text.
    """
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp_path = tmp.name

    saved_stdout_fd = os.dup(1)
    saved_stderr_fd = os.dup(2)
    try:
        with open(tmp_path, "r+", encoding="utf-8") as tmp:
            os.dup2(tmp.fileno(), 1)
            os.dup2(tmp.fileno(), 2)
            try:
                func()
            finally:
                sys.stdout.flush()
                sys.stderr.flush()
                try:
                    ctypes.CDLL(None).fflush(None)
                except Exception:
                    pass
                os.fsync(1)
                os.fsync(2)
            tmp.seek(0)
            return tmp.read()
    finally:
        os.dup2(saved_stdout_fd, 1)
        os.dup2(saved_stderr_fd, 2)
        os.close(saved_stdout_fd)
        os.close(saved_stderr_fd)
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def extract_rol_tr_flags(rol_output):
    """Extract the tr_flag values from an ROL trust-region solver log.

    Parameters
    ----------
    rol_output : str, os.PathLike, or text stream
        Either the raw ROL solver output as text, a path to a log file, or a
        file-like object with a ``read`` method.

    Returns
    -------
    list[int]
        The sequence of tr_flag values found in the solver output.
    """
    if hasattr(rol_output, "read"):
        text = rol_output.read()
    elif isinstance(rol_output, (str, os.PathLike)):
        try:
            path = Path(rol_output)
            if path.exists():
                text = path.read_text(encoding="utf-8", errors="replace")
            else:
                text = str(rol_output)
        except OSError:
            text = str(rol_output)
    else:
        text = str(rol_output)

    tr_flags = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        tokens = line.split()
        if len(tokens) < 8:
            continue
        if not tokens[0].lstrip("+-").isdigit():
            continue

        try:
            tr_flags.append(int(tokens[-1]))
        except ValueError:
            continue

    return tr_flags
