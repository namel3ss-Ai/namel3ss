import sys
from namel3ss.cli.main import main

if __name__ == "__main__":
    if not sys.argv[1:]:
        # If run as `python -m namel3ss` with no args, show help but also specific hints
        # that this is the fallback mode.
        print("namel3ss (python module mode)", file=sys.stderr)
        print("Tip: 'n3' is the preferred command.", file=sys.stderr)
        print("", file=sys.stderr)
    
    sys.exit(main())
