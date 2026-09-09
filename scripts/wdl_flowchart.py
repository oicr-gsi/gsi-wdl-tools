#!/usr/bin/env python3
"""Console script entry point for the WDL flowchart generator.

The tool itself lives in gsi_wdl_tools.wdl_flowchart so that other tools here -
generate_markdown_readme.py in particular - can import it. `main` is re-exported for the
generate-wdl-flowchart entry point declared in pyproject.toml.
"""

import sys
from pathlib import Path

# Let this also run as a plain script from a checkout, where the project root is not on
# sys.path. Installed, the inserted path is the package's own directory and changes nothing.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gsi_wdl_tools.wdl_flowchart import main  # noqa: E402

__all__ = ['main']

if __name__ == '__main__':
    main()
