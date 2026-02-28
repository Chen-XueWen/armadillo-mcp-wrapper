import argparse
import json
import logging
import os
import shlex
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import anyio
from mcp import types
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server import stdio as server_stdio
from mcp.server.lowlevel import NotificationOptions, Server

# Add project root to sys.path to allow imports from shared/backend.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.policy_engine import PolicyEngine
from backend.policy_runtime import (
    PolicyBlockedError,
    PolicyDeniedError,
    PolicyTimeoutError,
    enforce_policy,
    finalize_request_status,
)
from shared.db import init_db

LOGGER = logging.getLogger("governor.mcp.wrapper")


@dataclass
class UpstreamConfig:
    command: str
    args: List[str] = field(default_factory=list)
    cwd: Optional[str] = None
    env: Optional[Dict[str, str]] = None


class GovernorMCPProxy:
    def __init__(
        self,
        upstream: UpstreamConfig,
        policy_path: str,
        default_agent_id: str,
        review_timeout_seconds: int,
        agent_id_argument: str,
    ) -> None:
        self._upstream = upstream
        self._default_agent_id = default_agent_id or "Unknown"
        self._agent_id_argument = agent_id_argument
        self._review_timeout_seconds = max(1, review_timeout_seconds)
        self._policy_engine = PolicyEngine(policy_path=policy_path)
        self._session: Optional[ClientSession] = None
        self._tools: Dict[str, types.Tool] = {}

        self.server = Server(
            name="Governor MCP Wrapper",
            instructions=(
                "Policy-governed MCP wrapper. Tool calls are evaluated and audited before "
                "forwarding to the upstream MCP server."
            ),
        )
        self._register_handlers()

    def _register_handlers(self) -> None:
        @self.server.list_tools()
        async def list_tools_handler() -> List[types.Tool]:
            return [tool for _, tool in sorted(self._tools.items(), key=lambda item: item[0])]

        @self.server.call_tool(validate_input=True)
        async def call_tool_handler(tool_name: str, arguments: Dict[str, Any]) -> types.CallToolResult:
            return await self._proxy_call(tool_name, arguments or {})

    async def _proxy_call(self, tool_name: str, arguments: Dict[str, Any]) -> types.CallToolResult:
        if self._session is None:
            return self._error_result("Upstream MCP session is not initialized")

        upstream_args = dict(arguments)
        agent_id = self._extract_agent_id(upstream_args)

        try:
            decision = await enforce_policy(
                policy_engine=self._policy_engine,
                tool_name=tool_name,
                args=upstream_args,
                agent_id=agent_id,
                timeout_seconds=self._review_timeout_seconds,
                auto_complete_allow=False,
            )
        except PolicyBlockedError as exc:
            return self._error_result(f"Blocked by policy: {exc}")
        except PolicyDeniedError as exc:
            return self._error_result(str(exc))
        except PolicyTimeoutError as exc:
            return self._error_result(str(exc))

        request_id = decision.request_id

        try:
            result = await self._session.call_tool(name=tool_name, arguments=upstream_args)
        except Exception as exc:
            finalize_request_status(request_id, "FAILED")
            LOGGER.exception("Upstream tool call failed for '%s'", tool_name)
            return self._error_result(f"Upstream execution failed: {exc}")

        if result.isError:
            finalize_request_status(request_id, "FAILED")
        else:
            finalize_request_status(request_id, "COMPLETED")

        if not request_id:
            return result

        metadata = dict(result.meta or {})
        metadata["governor_request_id"] = request_id
        return result.model_copy(update={"meta": metadata})

    async def _load_upstream_tools(self) -> None:
        if self._session is None:
            raise RuntimeError("Cannot load tools before upstream session is ready")

        tools: Dict[str, types.Tool] = {}
        cursor: Optional[str] = None
        while True:
            listed = await self._session.list_tools(cursor=cursor)
            for tool in listed.tools:
                tools[tool.name] = tool
            cursor = listed.nextCursor
            if not cursor:
                break

        self._tools = tools
        LOGGER.info("Loaded %d upstream tools", len(self._tools))

    def _extract_agent_id(self, tool_args: Dict[str, Any]) -> str:
        value = tool_args.pop(self._agent_id_argument, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value is not None:
            return str(value)
        return self._default_agent_id

    @staticmethod
    def _error_result(message: str) -> types.CallToolResult:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=message)],
            isError=True,
        )

    async def run(self) -> None:
        init_db()

        LOGGER.info(
            "Starting wrapper against upstream command: %s %s",
            self._upstream.command,
            " ".join(self._upstream.args),
        )

        server_params = StdioServerParameters(
            command=self._upstream.command,
            args=self._upstream.args,
            cwd=self._upstream.cwd,
            env=self._upstream.env,
        )

        async with stdio_client(server_params, errlog=sys.stderr) as (upstream_read, upstream_write):
            async with ClientSession(upstream_read, upstream_write) as session:
                await session.initialize()
                self._session = session
                await self._load_upstream_tools()

                init_options = self.server.create_initialization_options(
                    notification_options=NotificationOptions(tools_changed=False)
                )
                async with server_stdio.stdio_server() as (read_stream, write_stream):
                    await self.server.run(read_stream, write_stream, init_options)


def _parse_command_args(raw: str) -> List[str]:
    text = (raw or "").strip()
    if not text:
        return []
    if text.startswith("["):
        loaded = json.loads(text)
        if not isinstance(loaded, list):
            raise ValueError("UPSTREAM_MCP_ARGS JSON must be a list of strings")
        return [str(item) for item in loaded]
    return shlex.split(text)


def _parse_env_json(raw: Optional[str]) -> Optional[Dict[str, str]]:
    if not raw:
        return None
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise ValueError("UPSTREAM_MCP_ENV_JSON must be a JSON object")
    return {str(key): str(value) for key, value in loaded.items()}


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Governor MCP governance wrapper")
    parser.add_argument("--upstream-command", default=os.getenv("UPSTREAM_MCP_COMMAND"))
    parser.add_argument("--upstream-args", default=os.getenv("UPSTREAM_MCP_ARGS", ""))
    parser.add_argument("--upstream-arg", action="append", default=[])
    parser.add_argument("--upstream-cwd", default=os.getenv("UPSTREAM_MCP_CWD"))
    parser.add_argument("--upstream-env-json", default=os.getenv("UPSTREAM_MCP_ENV_JSON"))
    parser.add_argument("--policy-path", default=os.getenv("GOVERNOR_POLICY_PATH", "policy.yaml"))
    parser.add_argument("--agent-id", default=os.getenv("GOVERNOR_AGENT_ID", "Unknown"))
    parser.add_argument(
        "--agent-id-argument",
        default=os.getenv("GOVERNOR_AGENT_ID_ARGUMENT", "__governor_agent_id"),
    )
    parser.add_argument(
        "--review-timeout-seconds",
        type=int,
        default=int(os.getenv("GOVERNOR_REVIEW_TIMEOUT_SECONDS", "60")),
    )
    parser.add_argument("--log-level", default=os.getenv("GOVERNOR_LOG_LEVEL", "INFO"))
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    if not args.upstream_command:
        parser.error(
            "Missing upstream MCP command. Provide --upstream-command or UPSTREAM_MCP_COMMAND."
        )

    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    try:
        parsed_args = _parse_command_args(args.upstream_args)
        parsed_args.extend(args.upstream_arg)
        upstream_env = _parse_env_json(args.upstream_env_json)
    except (ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
        return

    proxy = GovernorMCPProxy(
        upstream=UpstreamConfig(
            command=args.upstream_command,
            args=parsed_args,
            cwd=args.upstream_cwd,
            env=upstream_env,
        ),
        policy_path=args.policy_path,
        default_agent_id=args.agent_id,
        review_timeout_seconds=args.review_timeout_seconds,
        agent_id_argument=args.agent_id_argument,
    )

    anyio.run(proxy.run)


if __name__ == "__main__":
    main()
