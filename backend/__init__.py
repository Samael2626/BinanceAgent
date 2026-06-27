import sys


def _configure_stdio() -> None:
    """
    Force UTF-8 console output when the runtime supports it.
    On Windows this prevents emoji/log output from crashing with charmap errors.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_configure_stdio()
