"""Legacy batch enrichment runner.

This script is kept for backward compatibility and delegates to
`bible_api.batch_enrichment.main()`.
"""

from bible_api.batch_enrichment import main


if __name__ == "__main__":
    main()
