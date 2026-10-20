"""Small, bounded retries for atomic save replacement on Windows."""
import os
import time


def atomic_replace(source, target, attempts=5):
    """Replace a save file, tolerating brief scanner/indexer file locks."""
    for attempt in range(attempts):
        try:
            os.replace(source, target)
            return
        except OSError:
            if attempt == attempts-1:
                raise
            time.sleep(0.01*(attempt+1))
