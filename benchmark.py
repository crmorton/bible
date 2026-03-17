"""Legacy benchmark runner.

This script exists for backwards compatibility and delegates to
`bible_api.benchmark.main()`.
"""

from bible_api.benchmark import main


if __name__ == "__main__":
    main()
