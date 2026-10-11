import time
import logging
from typing import Optional, Callable, Dict, Any, List
import httpx

from app.importers.bzp_dto import BzpNoticeDTO

logger = logging.getLogger(__name__)

BZP_BASE_URL = "http://ezamowienia.gov.pl/mo-board/api/v1/notice"

BZP_NOTICE_TYPES = [
    "PlanPostepowania",
    "OgloszenieOWprowadzeniuSystemuKwalifikowaniaWykonawcow",
    "OgloszenieOZamowieniu",
    "OgloszenieOZamiarzeZawarciaUmowy",
    "OgloszenieOAtrakcyjnosciHandlowej",
    "OgloszenieOWynikuPostepowania",
    "OgloszenieOZmianieUmowy",
    "OgloszenieOKonkursie",
    "OgloszenieOWynikachKonkursu",
    "OgloszenieOZmianieOgloszenia",
    "OgloszenieOSprostowaniu"
]

def fetch_bzp_notices_page(
    client: Optional[httpx.Client] = None,
    notice_type: Optional[str] = None,
    publication_date_from: Optional[str] = None,
    publication_date_to: Optional[str] = None,
    search_after: Optional[str] = None,
    page_size: int = 100,
    fetch_fn: Optional[Callable[..., Any]] = None
) -> Dict[str, Any]:
    if fetch_fn is not None:
        return fetch_fn(
            notice_type=notice_type,
            publication_date_from=publication_date_from,
            publication_date_to=publication_date_to,
            search_after=search_after,
            page_size=page_size
        )

    params: Dict[str, Any] = {"pageSize": page_size}
    if notice_type:
        params["NoticeType"] = notice_type
    if publication_date_from:
        params["PublicationDateFrom"] = publication_date_from
    if publication_date_to:
        params["PublicationDateTo"] = publication_date_to
    if search_after:
        params["SearchAfter"] = search_after

    close_client = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        close_client = True

    max_retries = 5
    backoff_factor = 1.0

    try:
        for attempt in range(max_retries):
            try:
                response = client.get(BZP_BASE_URL, params=params)
                if response.status_code in (429, 403, 500, 502, 503, 504):
                    logger.warning(f"BZP API returned status {response.status_code}. Attempt {attempt + 1}/{max_retries}. Retrying...")
                    time.sleep(backoff_factor * (2 ** attempt))
                    continue
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as exc:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to fetch BZP notices after {max_retries} attempts: {exc}")
                    raise
                time.sleep(backoff_factor * (2 ** attempt))
        raise RuntimeError("Failed to fetch BZP notices due to max retries exceeded")
    finally:
        if close_client:
            client.close()


def fetch_all_bzp_notices(
    notice_type: Optional[str] = None,
    publication_date_from: Optional[str] = None,
    publication_date_to: Optional[str] = None,
    max_pages: Optional[int] = None,
    page_size: int = 100,
    fetch_fn: Optional[Callable[..., Any]] = None
) -> List[Dict[str, Any]]:
    all_notices = []
    search_after = None
    pages_fetched = 0

    client = httpx.Client(timeout=30.0) if fetch_fn is None else None

    try:
        while True:
            if max_pages is not None and pages_fetched >= max_pages:
                break

            data = fetch_bzp_notices_page(
                client=client,
                notice_type=notice_type,
                publication_date_from=publication_date_from,
                publication_date_to=publication_date_to,
                search_after=search_after,
                page_size=page_size,
                fetch_fn=fetch_fn
            )

            items = data if isinstance(data, list) else data.get("items", data.get("notices", []))
            if not items:
                break

            all_notices.extend(items)
            pages_fetched += 1

            # Determine next search_after / objectId
            last_item = items[-1]
            next_cursor = last_item.get("objectId") or last_item.get("objectId")
            if not next_cursor or next_cursor == search_after or len(items) < page_size:
                break
            search_after = next_cursor

    finally:
        if client:
            client.close()

    return all_notices
