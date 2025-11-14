import httpx
from typing import Optional, Dict, Any

class HTTPResponse:
    def __init__(self, status_code: int, headers: Dict[str, Any], content: Any):
        self.status_code = status_code
        self.headers = headers
        self.content = content

    def to_dict(self):
        return {
            "status_code": self.status_code,
            "headers": dict(self.headers),
            "content": self.content,
        }

async def make_request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    xml_body: Optional[str] = None,
) -> HTTPResponse:
    """
    Makes an asynchronous HTTP request to a specified URL.

    Args:
        method: The HTTP method (e.g., 'GET', 'POST').
        url: The URL to make the request to.
        headers: A dictionary of request headers.
        params: A dictionary of query parameters.
        json_body: A dictionary to be sent as a JSON request body.
        xml_body: A string to be sent as an XML request body.

    Returns:
        An HTTPResponse object containing the status code, headers, and content.
    """
    try:
        async with httpx.AsyncClient() as client:
            request_kwargs = {
                "method": method.upper(),
                "url": url,
                "headers": headers,
                "params": params,
            }
            if json_body:
                request_kwargs["json"] = json_body
            elif xml_body:
                # Ensure headers dict exists
                if request_kwargs["headers"] is None:
                    request_kwargs["headers"] = {}
                request_kwargs["headers"]['Content-Type'] = 'application/xml'
                request_kwargs["content"] = xml_body.encode('utf-8')

            response = await client.request(**request_kwargs)
            response.raise_for_status()  # Raise an exception for 4XX/5XX responses

            # Try to parse JSON, otherwise return text
            try:
                content = response.json()
            except Exception:
                content = response.text

            return HTTPResponse(
                status_code=response.status_code,
                headers=response.headers,
                content=content
            )
    except httpx.HTTPStatusError as e:
        # Handle HTTP errors (e.g., 404, 500)
        return HTTPResponse(
            status_code=e.response.status_code,
            headers=e.response.headers,
            content={"error": f"HTTP error: {e.response.status_code} {e.response.reason_phrase}"}
        )
    except httpx.RequestError as e:
        # Handle network-related errors
        return HTTPResponse(
            status_code=500,
            headers={},
            content={"error": f"Request failed: {e}"}
        )
