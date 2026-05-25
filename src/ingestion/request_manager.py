from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Mapping

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

LOGGER = logging.getLogger(__name__)

DEFAULT_HEADERS: Mapping[str, str] = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Connection": "keep-alive",
}


class RequestError(RuntimeError):
    pass


class HttpStatusError(RequestError):
    def __init__(self, status_code: int, url: str) -> None:
        super().__init__(f"HTTP {status_code} for {url}")
        self.status_code = status_code
        self.url = url


@dataclass
class RequestManager:
    base_headers: Mapping[str, str] = field(default_factory=lambda: dict(DEFAULT_HEADERS))
    min_delay: float = 0.8
    max_delay: float = 2.0
    timeout: int = 30
    session: requests.Session = field(init=False)

    def __post_init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(dict(self.base_headers))

    def prime_nse_session(self) -> None:
        try:
            self.get("https://www.nseindia.com", allow_non_ok=True)
        except requests.RequestException as exc:
            LOGGER.warning("NSE session prime failed: %s", exc)

    def _sleep(self) -> None:
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)

    @retry(
        retry=retry_if_exception_type((requests.RequestException, HttpStatusError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.6, min=1, max=10),
        reraise=True,
    )
    def _request(self, method: str, url: str, **kwargs: object) -> requests.Response:
        self._sleep()
        response = self.session.request(method, url, timeout=self.timeout, **kwargs)
        if not response.ok:
            raise HttpStatusError(response.status_code, url)
        return response

    def get(self, url: str, **kwargs: object) -> requests.Response:
        allow_non_ok = bool(kwargs.pop("allow_non_ok", False))
        if allow_non_ok:
            self._sleep()
            return self.session.get(url, timeout=self.timeout, **kwargs)
        return self._request("GET", url, **kwargs)
