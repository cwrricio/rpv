"""Testes unitários do cliente HTTP unificado (issue #9).

Cobrem cache, retry com backoff e propagação de HTTPError, sem tocar rede real.
"""
import time
import pytest
import requests
from unittest.mock import patch, MagicMock

from functions.common import http_client


@pytest.fixture(autouse=True)
def limpar_cache():
    http_client.clear_cache()
    yield
    http_client.clear_cache()


def _mock_response(status: int = 200, body: dict | None = None):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.json.return_value = body or {"ok": True}
    if status >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    else:
        resp.raise_for_status.return_value = None
    return resp


def test_retorna_json_em_sucesso():
    with patch("requests.get", return_value=_mock_response(200, {"x": 1})):
        result = http_client.get("https://api.example.com/test", cache_ttl=0)
    assert result == {"x": 1}


def test_cache_evita_segunda_requisicao():
    mock = MagicMock(return_value=_mock_response(200, {"cached": True}))
    with patch("requests.get", mock):
        http_client.get("https://api.example.com/cache", cache_ttl=60)
        http_client.get("https://api.example.com/cache", cache_ttl=60)
    assert mock.call_count == 1


def test_cache_ttl_zero_nao_armazena():
    mock = MagicMock(return_value=_mock_response(200, {"v": 1}))
    with patch("requests.get", mock):
        http_client.get("https://api.example.com/nocache", cache_ttl=0)
        http_client.get("https://api.example.com/nocache", cache_ttl=0)
    assert mock.call_count == 2


def test_retry_em_timeout():
    mock = MagicMock(side_effect=requests.Timeout("timeout"))
    with patch("requests.get", mock), patch("time.sleep"):
        with pytest.raises(requests.Timeout):
            http_client.get("https://api.example.com/slow", retries=3, cache_ttl=0)
    assert mock.call_count == 3


def test_retry_em_connection_error():
    mock = MagicMock(side_effect=requests.ConnectionError("conn"))
    with patch("requests.get", mock), patch("time.sleep"):
        with pytest.raises(requests.ConnectionError):
            http_client.get("https://api.example.com/down", retries=2, cache_ttl=0)
    assert mock.call_count == 2


def test_http_error_4xx_nao_retenta():
    mock = MagicMock(return_value=_mock_response(404))
    with patch("requests.get", mock):
        with pytest.raises(requests.HTTPError):
            http_client.get("https://api.example.com/notfound", retries=3, cache_ttl=0)
    assert mock.call_count == 1


def test_sucesso_na_segunda_tentativa():
    resps = [requests.Timeout("t"), _mock_response(200, {"retry": True})]
    mock = MagicMock(side_effect=resps)
    with patch("requests.get", mock), patch("time.sleep"):
        result = http_client.get("https://api.example.com/flaky", retries=3, cache_ttl=0)
    assert result == {"retry": True}
    assert mock.call_count == 2
