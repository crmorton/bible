"""Client helpers for consuming the Bible API."""

import concurrent.futures
import logging
from urllib.parse import quote

try:
    import requests
    from requests.adapters import HTTPAdapter
except ImportError:  # pragma: no cover
    requests = None
    HTTPAdapter = None


logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


class BibleAPIClient:
    def __init__(self, base_url="http://localhost:8000/passage", max_workers=50):
        if requests is None:
            raise ImportError(
                "The 'requests' package is required for BibleAPIClient. "
                "Install with: pip install requests"
            )

        self.base_url = base_url
        self.max_workers = max_workers

        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=max_workers, pool_maxsize=max_workers)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def _fetch_single(self, item, translation):
        passage_id = item['id']
        osis_ref = item['osis']
        encoded_ref = quote(f"osis:{osis_ref}")
        url = f"{self.base_url}?ref={encoded_ref}&translation={translation}"

        result = {
            "id": passage_id,
            "osis": osis_ref,
            "html": None,
            "success": False,
            "error": None,
        }

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            if "html" not in data:
                raise ValueError("Response JSON missing 'html' key")
            result["html"] = data["html"]
            result["success"] = True
        except requests.exceptions.RequestException as e:
            result["error"] = f"HTTP Error: {e}"
        except Exception as e:
            result["error"] = f"Unexpected Error: {e}"

        return result

    def fetch_batch(self, items, translation="LEB"):
        results = []
        total = len(items)
        logging.info(f"Starting batch fetch for {total} passages using {self.max_workers} workers...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._fetch_single, item, translation): item for item in items}
            for count, future in enumerate(concurrent.futures.as_completed(futures), 1):
                results.append(future.result())
                if count % 500 == 0 or count == total:
                    logging.info(f"Progress: {count}/{total} passages fetched.")

        return results
