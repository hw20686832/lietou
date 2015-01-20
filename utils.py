# coding:utf-8
import requests
from tornalet import asyncify
from tornado.httpclient import AsyncHTTPClient

AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")


class AsyncHTTPAdapter(requests.adapters.HTTPAdapter):
    def send(self, request, stream=False, timeout=None,
             verify=True, cert=None, proxies=None):
        http_client = AsyncHTTPClient()
        http_response = asyncify(http_client.fetch)(request=request.url,
                                                    method=request.method,
                                                    body=request.body,
                                                    headers=request.headers)

        http_response.reason = 'Unknown'
        http_response.content = http_response.body
        response = self.build_response(request, http_response)

        response.status_code = http_response.code
        response._content = http_response.content

        return response
