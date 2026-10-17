from __future__ import annotations

import requests


class WebChallengeError(requests.HTTPError):
    """
    The server answered with a bot challenge
    (Cloudflare `cf-mitigated: challenge`)

    Can not retry

    """

    pass
