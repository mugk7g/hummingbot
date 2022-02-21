from base64 import b64encode
from datetime import datetime
import hashlib
import hmac

from typing import (
    Dict
)
from urllib.parse import urlencode

from hummingbot.connector.exchange.coinflex.coinflex_http_utils import (
    CoinflexRESTRequest,
)
from hummingbot.connector.time_synchronizer import TimeSynchronizer
from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import WSRequest


class CoinflexAuth(AuthBase):

    def __init__(self, api_key: str, secret_key: str, time_provider: TimeSynchronizer):
        self.api_key = api_key
        self.secret_key = secret_key
        self.time_provider = time_provider

    async def rest_authenticate(self, request: CoinflexRESTRequest) -> CoinflexRESTRequest:
        """
        Adds the server time and the signature to the request, required for authenticated interactions. It also adds
        the required parameter in the request header.
        :param request: the request to be configured for authenticated interaction
        """

        headers = {}
        if request.headers is not None:
            headers.update(request.headers)
        headers.update(self._header_for_authentication(request))
        request.headers = headers

        return request

    async def ws_authenticate(self, request: WSRequest) -> WSRequest:
        """
        This method is intended to configure a websocket request to be authenticated.
        It should be used with empty requests to send an initial login payload.
        :param request: the request to be configured for authenticated interaction
        """
        time_now = self.time_provider.time()
        tag = datetime.fromtimestamp(int(time_now)).isoformat()
        timestamp = int(time_now * 1e3)

        request.payload = {
            "op": "login",
            "tag": tag,
            "data": {
                "apiKey": self.api_key,
                "timestamp": timestamp,
                "signature": self._generate_signature_ws(timestamp),
            }
        }
        return request

    def _header_for_authentication(self,
                                   request: CoinflexRESTRequest) -> Dict[str, str]:
        time_now = self.time_provider.time()
        timestamp = datetime.fromtimestamp(int(time_now)).isoformat()
        nonce = int(time_now * 1e3)

        signature = self._generate_signature(timestamp,
                                             nonce,
                                             request)

        return {
            "AccessKey": self.api_key,
            "Timestamp": timestamp,
            "Signature": signature,
            "Nonce": str(nonce),
        }

    def _generate_signature(self,
                            timestamp: str,
                            nonce: int,
                            request: WSRequest) -> str:

        if request.should_use_data:
            request_params = request.data or ""
        else:
            request_params = urlencode(request.params or {})

        payload = '{}\n{}\n{}\n{}\n{}\n{}'.format(timestamp,
                                                  nonce,
                                                  request.method,
                                                  request.auth_url,
                                                  request.auth_path,
                                                  request_params)

        digest = hmac.new(self.secret_key.encode("utf8"), payload.encode("utf8"), hashlib.sha256).digest()
        return b64encode(digest).decode().strip()

    def _generate_signature_ws(self,
                               timestamp: int) -> str:

        payload = f"{timestamp}GET/auth/self/verify"

        digest = hmac.new(self.secret_key.encode("utf8"), payload.encode("utf8"), hashlib.sha256).digest()
        return b64encode(digest).decode().strip()
