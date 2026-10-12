"""Edge CLI compatibility until the endpoint migration is released upstream.

See https://github.com/rany2/edge-tts/pull/491. Keep this adapter in the
application so installed dependencies remain unchanged and rollback is simple.
"""

from urllib.parse import urlsplit

from edge_tts import communicate, constants
from edge_tts.util import main


def configure_synthesis_endpoint() -> None:
    # Newer library releases should retain their own endpoint configuration.
    if urlsplit(communicate.WSS_URL).hostname == "speech.platform.bing.com":
        communicate.WSS_URL = (
            "wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1"
            f"?Ocp-Apim-Subscription-Key={constants.TRUSTED_CLIENT_TOKEN}"
        )


if __name__ == "__main__":
    configure_synthesis_endpoint()
    main()
