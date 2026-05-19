import struct

import httpx
import pytest

from portainer_cli.client import PortainerClient, PortainerError


def _mock_client(responses: list[httpx.Response]) -> PortainerClient:
    client = PortainerClient("http://example.com", "key")

    def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    client.client = httpx.Client(transport=httpx.MockTransport(handler))
    return client


def test_get_endpoint_by_name():
    client = _mock_client([
        httpx.Response(200, json=[
            {"Id": 1, "Name": "primary"},
            {"Id": 2, "Name": "secondary"},
        ])
    ])
    ep = client.get_endpoint_by_name("primary")
    assert ep["Id"] == 1


def test_get_endpoint_by_name_not_found():
    client = _mock_client([
        httpx.Response(200, json=[{"Id": 1, "Name": "primary"}])
    ])
    with pytest.raises(PortainerError, match="not found"):
        client.get_endpoint_by_name("missing")


def test_get_stacks():
    client = _mock_client([
        httpx.Response(200, json=[{"Id": 1, "Name": "stack1"}])
    ])
    stacks = client.get_stacks()
    assert stacks == [{"Id": 1, "Name": "stack1"}]


def test_get_stack_by_name():
    client = _mock_client([
        httpx.Response(200, json=[
            {"Id": 1, "Name": "foo"},
            {"Id": 2, "Name": "bar"},
        ])
    ])
    s = client.get_stack_by_name("bar")
    assert s["Id"] == 2


def test_get_stack_by_name_not_found():
    client = _mock_client([
        httpx.Response(200, json=[{"Id": 1, "Name": "foo"}])
    ])
    with pytest.raises(PortainerError, match="not found"):
        client.get_stack_by_name("missing")


def test_redeploy_stack_git():
    client = _mock_client([
        httpx.Response(200, json=[{
            "Id": 1, "Name": "mystack", "EndpointId": 5,
            "GitConfig": {"URL": "https://...", "ReferenceName": "refs/heads/main"},
        }]),
        httpx.Response(200, json={}),
    ])
    msg = client.redeploy_stack("mystack")
    assert "redeployed" in msg


def test_redeploy_stack_file():
    client = _mock_client([
        httpx.Response(200, json=[{
            "Id": 1, "Name": "mystack", "EndpointId": 5,
        }]),
        httpx.Response(200, json={"StackFileContent": "version: '3'", "Env": []}),
        httpx.Response(200, json={}),
    ])
    msg = client.redeploy_stack("mystack")
    assert "redeployed" in msg


def test_auth_error():
    client = _mock_client([
        httpx.Response(401, text="unauthorized"),
    ])
    with pytest.raises(PortainerError, match="Authentication failed"):
        client.get_stacks()


def test_format_stack_list():
    client = PortainerClient("http://x", "k")
    stacks = [
        {"Id": 1, "Name": "alpha", "Type": 1, "Status": 1, "EndpointId": 10},
        {"Id": 2, "Name": "beta", "Type": 2, "Status": 2, "EndpointId": 20,
         "GitConfig": {"URL": "https://repo.git"}},
    ]
    out = client.format_stack_list(stacks)
    assert "alpha" in out
    assert "swarm" in out
    assert "compose" in out
    assert "https://repo.git" in out


def test_fetch_logs():
    def _frame(stype: int, content: bytes) -> bytes:
        return struct.pack(">BxxxI", stype, len(content)) + content

    client = _mock_client([
        httpx.Response(200, content=_frame(1, b"line1\n") + _frame(2, b"line2\n")),
    ])
    logs = client.fetch_logs(1, "abc123")
    assert logs == [(1, "line1\n"), (2, "line2\n")]
