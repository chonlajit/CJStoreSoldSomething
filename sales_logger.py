"""CJStore Sales Logger Wrapper.

Delegates to cjSales_loggers.py for backward compatibility.
"""

import sys
from cjSales_loggers import append_to_sheet, main, send_notification

if __name__ == "__main__":
    sys.exit(main())
