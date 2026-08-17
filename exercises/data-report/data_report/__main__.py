# [Implementation 1]
# Module execution shares the same exit contract as the installed console script.
from .cli import main

raise SystemExit(main())
