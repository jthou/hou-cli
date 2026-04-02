"""shared.httpx_defaults：NO_PROXY 合并、trust_env 开关。"""
import os

from shared.httpx_defaults import (
    httpx_default_network_kwargs,
    httpx_trust_env_disabled,
    httpx_uses_environment_proxy,
    merge_hou_cli_no_proxy_hosts,
)


def test_default_uses_trust_env_and_empty_kwargs(monkeypatch):
    monkeypatch.delenv("HTTPX_TRUST_ENV", raising=False)
    assert httpx_trust_env_disabled() is False
    assert httpx_uses_environment_proxy() is True
    assert httpx_default_network_kwargs() == {}


def test_HTTPX_TRUST_ENV_0_disables_trust_env(monkeypatch):
    monkeypatch.setenv("HTTPX_TRUST_ENV", "0")
    assert httpx_trust_env_disabled() is True
    assert httpx_uses_environment_proxy() is False
    assert httpx_default_network_kwargs() == {"trust_env": False, "proxy": None}


def test_merge_no_proxy_adds_jthou_and_wiki_host(monkeypatch):
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)
    monkeypatch.setenv("MEDIAWIKI_URL", "http://wiki.example.com/mediawiki")
    merge_hou_cli_no_proxy_hosts()
    assert "www.jthou.com" in os.environ["NO_PROXY"]
    assert "127.0.0.1" in os.environ["NO_PROXY"]
    assert "wiki.example.com" in os.environ["NO_PROXY"]
    assert "www.jthou.com" in os.environ["no_proxy"]


def test_merge_no_proxy_preserves_star(monkeypatch):
    monkeypatch.setenv("NO_PROXY", "*")
    merge_hou_cli_no_proxy_hosts()
    assert os.environ["NO_PROXY"] == "*"


def test_HTTPX_NO_PROXY_EXTRA(monkeypatch):
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("MEDIAWIKI_URL", raising=False)
    monkeypatch.setenv("HTTPX_NO_PROXY_EXTRA", "intranet.corp.local")
    merge_hou_cli_no_proxy_hosts()
    assert "intranet.corp.local" in os.environ["NO_PROXY"]
