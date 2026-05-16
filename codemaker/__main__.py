"""Allow running as `python -m codemaker`."""

import sys
import traceback

try:
    from .main import main
    main()
except Exception as exc:
    # Ensure any startup crash is visible in launchd logs
    print(f"[CodeMaker] FATAL: {exc}", file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
