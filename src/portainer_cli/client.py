import struct

import httpx


class PortainerError(Exception):
    def __init__(self, message, status_code=None):
        self.status_code = status_code
        super().__init__(message)


class LogStreamParser:
    def __init__(self):
        self.buf = bytearray()

    def feed(self, data: bytes):
        self.buf.extend(data)

    def frames(self):
        frames = []
        while True:
            if len(self.buf) < 8:
                break
            sz = struct.unpack(">I", bytes(self.buf[4:8]))[0]
            if len(self.buf) < 8 + sz:
                break
            stream_type = self.buf[0]
            content = bytes(self.buf[8 : 8 + sz])
            frames.append((stream_type, content))
            del self.buf[: 8 + sz]
        return frames

    def flush(self):
        if self.buf:
            frames = [(1, bytes(self.buf))]
            self.buf.clear()
            return frames
        return []


class PortainerClient:
    def __init__(self, url: str, api_key: str):
        self.base = url.rstrip("/")
        self.client = httpx.Client(
            headers={"X-API-KEY": api_key},
            timeout=30,
        )

    def _req(self, method: str, path: str, **kwargs):
        url = f"{self.base}{path}"
        try:
            r = self.client.request(method, url, **kwargs)
        except httpx.ConnectError as e:
            raise PortainerError(f"Connection failed: {e}")
        except httpx.TimeoutException as e:
            raise PortainerError(f"Request timed out: {e}")

        if r.status_code == 401:
            raise PortainerError("Authentication failed: invalid API key", 401)
        if r.status_code == 404:
            raise PortainerError("Resource not found", 404)
        if r.status_code >= 400:
            detail = r.text.strip()[:200]
            raise PortainerError(
                f"Request failed ({r.status_code}): {detail}", r.status_code
            )
        return r

    def get_endpoint_by_name(self, name: str) -> dict:
        r = self._req("GET", "/api/endpoints")
        endpoints = r.json()
        for ep in endpoints:
            if ep.get("Name") == name:
                return ep
        names = [ep.get("Name", "?") for ep in endpoints]
        raise PortainerError(
            f"Environment '{name}' not found. Available: {', '.join(names)}"
        )

    def get_stacks(self) -> list[dict]:
        r = self._req("GET", "/api/stacks")
        return r.json()

    def format_stack_list(self, stacks: list[dict]) -> str:
        type_names = {1: "swarm", 2: "compose", 3: "k8s"}
        status_names = {1: "active", 2: "inactive"}
        lines = []
        for s in stacks:
            sid = s["Id"]
            name = s.get("Name", "?")
            stype = type_names.get(s.get("Type", 0), "?")
            status = status_names.get(s.get("Status", 0), "?")
            ep = s.get("EndpointId", "?")

            git = ""
            gc = s.get("GitConfig") or {}
            if gc.get("URL"):
                git = f" git:{gc['URL']}"

            lines.append(
                f"{sid:<5} {name:<30} {stype:<8} status={status} endpoint={ep}{git}"
            )
        return "\n".join(lines)

    def get_stack_by_name(self, name: str) -> dict:
        r = self._req("GET", "/api/stacks")
        stacks = r.json()
        for s in stacks:
            if s.get("Name") == name:
                return s
        raise PortainerError(f"Stack '{name}' not found")

    def find_stacks(self, search: str) -> list[dict]:
        r = self._req("GET", "/api/stacks")
        stacks = r.json()
        search_lower = search.lower()
        matches = [s for s in stacks if search_lower in s.get("Name", "").lower()]
        matches.sort(
            key=lambda s: (
                0 if s["Name"].lower().startswith(search_lower) else 1,
                s["Name"],
            )
        )
        return matches

    def redeploy_stack(self, name: str, repull: bool = True) -> str:
        stack = self.get_stack_by_name(name)
        eid = stack["EndpointId"]
        sid = stack["Id"]
        sname = stack["Name"]

        is_git = bool(stack.get("GitConfig") and stack["GitConfig"].get("URL"))
        if is_git:
            return self._redeploy_stack_git(stack, eid, repull)
        return self._redeploy_stack_file(sid, eid, repull, sname)

    def _redeploy_stack_git(self, stack: dict, eid: int, repull: bool) -> str:
        gc = stack.get("GitConfig", {}) or {}
        payload: dict = {
            "RepositoryReferenceName": gc.get("ReferenceName", "refs/heads/main"),
            "RepullImageAndRedeploy": repull,
            "Prune": False,
        }
        auth = gc.get("Authentication")
        if auth:
            payload["RepositoryAuthentication"] = True
            if auth.get("Username"):
                payload["RepositoryUsername"] = auth["Username"]
            if auth.get("Password"):
                payload["RepositoryPassword"] = auth["Password"]
        self._req(
            "PUT",
            f"/api/stacks/{stack['Id']}/git/redeploy",
            params={"endpointId": eid},
            json=payload,
        )
        return f"Stack '{stack['Name']}' redeployed from git"

    def _redeploy_stack_file(self, sid: int, eid: int, repull: bool, sname: str) -> str:
        r = self._req("GET", f"/api/stacks/{sid}/file")
        data = r.json()
        payload = {
            "StackFileContent": data.get("StackFileContent", ""),
            "Env": data.get("Env", []),
            "Prune": False,
            "PullImage": repull,
        }
        self._req(
            "PUT",
            f"/api/stacks/{sid}",
            params={"endpointId": eid},
            json=payload,
        )
        return f"Stack '{sname}' redeployed"

    def get_service_by_name(self, endpoint_id: int, name: str) -> dict:
        filters = '{"name":["' + name + '"]}'
        r = self._req(
            "GET",
            f"/api/endpoints/{endpoint_id}/docker/services",
            params={"filters": filters, "status": True},
        )
        services = r.json()
        if not services:
            raise PortainerError(
                f"Service '{name}' not found in environment {endpoint_id}"
            )
        return services[0]

    def format_service_status(self, service: dict) -> str:
        spec = service.get("Spec", {})
        name = spec.get("Name", "?")
        template = spec.get("TaskTemplate", {})
        container = template.get("ContainerSpec", {})
        image = container.get("Image", "?")

        mode_dict = spec.get("Mode", {})
        if "Replicated" in mode_dict:
            replicas = mode_dict["Replicated"].get("Replicas", 1)
            mode = f"replicated ({replicas} replicas)"
        elif "Global" in mode_dict:
            mode = "global"
        else:
            mode = str(mode_dict)

        srv_status = service.get("ServiceStatus") or {}
        running = srv_status.get("RunningTasks", "?")
        desired = srv_status.get("DesiredTasks", "?")
        tasks = f"{running}/{desired} tasks running"

        update = service.get("UpdateStatus")
        update_str = ""
        if update:
            us = update.get("State", "?")
            msg = update.get("Message", "")
            update_str = f"\nUpdate: {us} {msg}".rstrip()

        created = service.get("CreatedAt", "?")
        ports = []
        ep_spec = spec.get("EndpointSpec", {})
        for p in ep_spec.get("Ports", []):
            published = p.get("PublishedPort", "")
            target = p.get("TargetPort", "")
            proto = p.get("Protocol", "")
            ports.append(f"{published}:{target}/{proto}")

        lines = [
            f"Name:    {name}",
            f"Image:   {image}",
            f"Mode:    {mode}",
            f"Tasks:   {tasks}",
            f"Created: {created}",
        ]
        if update_str:
            lines.append(update_str)
        if ports:
            lines.append(f"Ports:   {', '.join(ports)}")

        return "\n".join(lines)

    def fetch_logs(
        self, endpoint_id: int, service_id: str, tail: int | None = None
    ) -> list[tuple[int, str]]:
        params = {"stdout": "true", "stderr": "true", "timestamps": "true"}
        if tail is not None:
            params["tail"] = str(tail)

        r = self._req(
            "GET",
            f"/api/endpoints/{endpoint_id}/docker/services/{service_id}/logs",
            params=params,
        )
        content = r.content
        if not content:
            return []

        parser = LogStreamParser()
        parser.feed(content)
        frames = parser.frames()
        result = []
        for stype, data in frames:
            try:
                text = data.decode("utf-8", errors="replace")
            except Exception:
                text = repr(data)
            result.append((stype, text))
        return result

    def stream_logs(
        self,
        endpoint_id: int,
        service_id: str,
    ):
        params = {
            "stdout": "true",
            "stderr": "true",
            "timestamps": "true",
            "follow": "true",
        }

        url = (
            f"{self.base}/api/endpoints/{endpoint_id}/docker/services/{service_id}/logs"
        )
        parser = LogStreamParser()
        try:
            with self.client.stream(
                "GET", url, params=params, timeout=httpx.Timeout(None)
            ) as r:
                if r.status_code != 200:
                    raise PortainerError(
                        f"Log stream failed ({r.status_code}): {r.text[:200]}",
                        r.status_code,
                    )
                for chunk in r.iter_bytes():
                    if not chunk:
                        continue
                    parser.feed(chunk)
                    for stype, data in parser.frames():
                        try:
                            text = data.decode("utf-8", errors="replace")
                        except Exception:
                            text = repr(data)
                        yield stype, text
        except httpx.ReadTimeout:
            pass
        except KeyboardInterrupt:
            pass
        finally:
            leftover = parser.flush()
            for stype, data in leftover:
                try:
                    text = data.decode("utf-8", errors="replace")
                except Exception:
                    text = repr(data)
                yield stype, text
