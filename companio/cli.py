"""CLI commands for companio."""

import asyncio
import os
import select
import signal
import sys
from pathlib import Path

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    if sys.stdout.encoding != "utf-8":
        os.environ["PYTHONIOENCODING"] = "utf-8"
        # Re-open stdout/stderr with UTF-8 encoding
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text

from companio import __logo__, __version__
from companio.config.schema import Config
from companio.helpers import sync_workspace_templates

app = typer.Typer(
    name="companio",
    help=f"{__logo__} companio - Personal AI Assistant",
    no_args_is_help=True,
)

console = Console()
EXIT_COMMANDS = {"exit", "quit", "/exit", "/quit", ":q"}

# ---------------------------------------------------------------------------
# CLI input: prompt_toolkit for editing, paste, history, and display
# ---------------------------------------------------------------------------

_PROMPT_SESSION: PromptSession | None = None
_SAVED_TERM_ATTRS = None  # original termios settings, restored on exit


def _flush_pending_tty_input() -> None:
    """Drop unread keypresses typed while the model was generating output."""
    try:
        fd = sys.stdin.fileno()
        if not os.isatty(fd):
            return
    except Exception:
        return

    try:
        import termios

        termios.tcflush(fd, termios.TCIFLUSH)
        return
    except Exception:
        pass

    try:
        while True:
            ready, _, _ = select.select([fd], [], [], 0)
            if not ready:
                break
            if not os.read(fd, 4096):
                break
    except Exception:
        return


def _restore_terminal() -> None:
    """Restore terminal to its original state (echo, line buffering, etc.)."""
    if _SAVED_TERM_ATTRS is None:
        return
    try:
        import termios

        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, _SAVED_TERM_ATTRS)
    except Exception:
        pass


def _init_prompt_session() -> None:
    """Create the prompt_toolkit session with persistent file history."""
    global _PROMPT_SESSION, _SAVED_TERM_ATTRS

    # Save terminal state so we can restore it on exit
    try:
        import termios

        _SAVED_TERM_ATTRS = termios.tcgetattr(sys.stdin.fileno())
    except Exception:
        pass

    from companio.config.paths import get_cli_history_path

    history_file = get_cli_history_path()
    history_file.parent.mkdir(parents=True, exist_ok=True)

    _PROMPT_SESSION = PromptSession(
        history=FileHistory(str(history_file)),
        enable_open_in_editor=False,
        multiline=False,  # Enter submits (single line mode)
    )


def _print_agent_response(response: str, render_markdown: bool) -> None:
    """Render assistant response with consistent terminal styling."""
    content = response or ""
    body = Markdown(content) if render_markdown else Text(content)
    console.print()
    console.print(f"[cyan]{__logo__} companio[/cyan]")
    console.print(body)
    console.print()


def _is_exit_command(command: str) -> bool:
    """Return True when input should end interactive chat."""
    return command.lower() in EXIT_COMMANDS


async def _read_interactive_input_async() -> str:
    """Read user input using prompt_toolkit (handles paste, history, display).

    prompt_toolkit natively handles:
    - Multiline paste (bracketed paste mode)
    - History navigation (up/down arrows)
    - Clean display (no ghost characters or artifacts)
    """
    if _PROMPT_SESSION is None:
        raise RuntimeError("Call _init_prompt_session() first")
    try:
        with patch_stdout():
            return await _PROMPT_SESSION.prompt_async(
                HTML("<b fg='ansiblue'>You:</b> "),
            )
    except EOFError as exc:
        raise KeyboardInterrupt from exc


def version_callback(value: bool):
    if value:
        console.print(f"{__logo__} companio v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(None, "--version", "-v", callback=version_callback, is_eager=True),
):
    """companio - Personal AI Assistant."""
    pass


# ============================================================================
# Onboard / Setup
# ============================================================================


@app.command()
def onboard():
    """Initialize companio configuration and workspace."""
    from companio.config.loader import get_config_path, load_config, save_config
    from companio.config.schema import Config

    config_path = get_config_path()

    # If config already exists, ask what to do
    if config_path.exists():
        console.print(f"[yellow]Config already exists at {config_path}[/yellow]")
        if not typer.confirm("Re-run setup? (existing values will be used as defaults)", default=False):
            console.print("Aborted.")
            return
        config = load_config()
    else:
        config = Config()

    console.print(f"\n{__logo__} [bold]companio setup[/bold]\n")

    # --- Optional dependency check ---
    import shutil

    _OPTIONAL_DEPS = [
        {
            "name": "Node.js (npx)",
            "check": "npx",
            "install": "brew install node  (or https://nodejs.org/)",
            "used_by": "MCP servers (Playwright, GitHub, Slack, Filesystem)",
        },
        {
            "name": "Google Workspace CLI",
            "check": "gws",
            "install": "npm install -g @googleworkspace/cli",
            "used_by": "Google Workspace skill (Gmail, Drive, Calendar, Sheets)",
        },
    ]

    missing_deps = []
    for dep in _OPTIONAL_DEPS:
        if not shutil.which(dep["check"]):
            missing_deps.append(dep)

    if missing_deps:
        console.print("[bold yellow]Optional dependencies not found:[/bold yellow]\n")
        for dep in missing_deps:
            console.print(f"  [yellow]•[/yellow] [bold]{dep['name']}[/bold]")
            console.print(f"    Used by: {dep['used_by']}")
            console.print(f"    Install: [cyan]{dep['install']}[/cyan]")
        console.print("\n  [dim]These are optional — companio works without them, but related features will be unavailable.[/dim]\n")
    else:
        console.print("[green]✓[/green] All optional dependencies found.\n")

    # --- Step 1: LLM Provider ---
    console.print("[bold cyan]Step 1:[/bold cyan] LLM Provider")
    console.print("  Supported: Anthropic (Claude), OpenAI (GPT), Google Gemini")
    console.print("  You need at least one API key.\n")

    anthropic_key = typer.prompt(
        "  Anthropic API key (sk-ant-...)",
        default=config.providers.anthropic.api_key or "",
        show_default=False,
    )
    if anthropic_key:
        config.providers.anthropic.api_key = anthropic_key

    openai_key = typer.prompt(
        "  OpenAI API key (sk-...)",
        default=config.providers.openai.api_key or "",
        show_default=False,
    )
    if openai_key:
        config.providers.openai.api_key = openai_key

    gemini_key = typer.prompt(
        "  Gemini API key",
        default=config.providers.gemini.api_key or "",
        show_default=False,
    )
    if gemini_key:
        config.providers.gemini.api_key = gemini_key

    if not any([anthropic_key, openai_key, gemini_key]):
        console.print("  [yellow]Warning: No API keys set. You can add them later in config.json[/yellow]")

    # --- Step 2: Agent defaults ---
    console.print("\n[bold cyan]Step 2:[/bold cyan] Agent Settings")

    config.agents.defaults.model = typer.prompt(
        "  Default model",
        default=config.agents.defaults.model,
    )
    config.agents.defaults.provider = typer.prompt(
        "  Provider (auto / anthropic / openai / gemini)",
        default=config.agents.defaults.provider,
    )
    config.agents.defaults.workspace = typer.prompt(
        "  Workspace path",
        default=config.agents.defaults.workspace,
    )
    config.agents.defaults.max_tokens = int(typer.prompt(
        "  Max response tokens",
        default=str(config.agents.defaults.max_tokens),
    ))
    if not config.agents.defaults.reasoning_effort:
        config.agents.defaults.reasoning_effort = "medium"

    # --- Step 3: Telegram ---
    console.print("\n[bold cyan]Step 3:[/bold cyan] Telegram Integration")
    if typer.confirm("  Enable Telegram bot?", default=config.channels.telegram.enabled):
        config.channels.telegram.enabled = True
        token = typer.prompt(
            "  Bot token (from @BotFather)",
            default=config.channels.telegram.token or "",
            show_default=False,
        )
        if token:
            config.channels.telegram.token = token

        allow_from_str = typer.prompt(
            "  Allowed usernames (comma-separated)",
            default=",".join(config.channels.telegram.allow_from) if config.channels.telegram.allow_from else "",
            show_default=False,
        )
        if allow_from_str:
            config.channels.telegram.allow_from = [u.strip() for u in allow_from_str.split(",") if u.strip()]

        config.channels.telegram.reply_to_message = typer.confirm(
            "  Reply with quote?", default=config.channels.telegram.reply_to_message
        )
    else:
        config.channels.telegram.enabled = False

    # --- Step 4: Channel behavior ---
    console.print("\n[bold cyan]Step 4:[/bold cyan] Channel Behavior")
    config.channels.send_progress = typer.confirm(
        "  Stream text progress to channel?", default=config.channels.send_progress
    )
    config.channels.send_tool_hints = typer.confirm(
        "  Stream tool-call hints?", default=config.channels.send_tool_hints
    )

    # --- Step 5: Tools ---
    console.print("\n[bold cyan]Step 5:[/bold cyan] Tools")

    config.tools.restrict_to_workspace = typer.confirm(
        "  Restrict file access to workspace?", default=config.tools.restrict_to_workspace
    )

    # Web
    console.print("\n  [dim]Web tools:[/dim]")
    web_proxy = typer.prompt(
        "  Web proxy URL (empty for direct)",
        default=config.tools.web.proxy or "",
        show_default=False,
    )
    config.tools.web.proxy = web_proxy if web_proxy else None

    brave_key = typer.prompt(
        "  Brave Search API key",
        default=config.tools.web.search.api_key or "",
        show_default=False,
    )
    if brave_key:
        config.tools.web.search.api_key = brave_key

    config.tools.web.search.max_results = int(typer.prompt(
        "  Search max results",
        default=str(config.tools.web.search.max_results),
    ))

    # Obsidian
    console.print("\n  [dim]Obsidian integration:[/dim]")
    if typer.confirm("  Enable Obsidian vault?", default=config.tools.obsidian.enabled):
        config.tools.obsidian.enabled = True
        vault_path = typer.prompt(
            "  Vault path (e.g. ~/Documents/Obsidian/MyVault)",
            default=config.tools.obsidian.vault_path or "",
            show_default=False,
        )
        if vault_path:
            config.tools.obsidian.vault_path = vault_path
    else:
        config.tools.obsidian.enabled = False

    # --- Step 6: MCP Servers ---
    console.print("\n[bold cyan]Step 6:[/bold cyan] MCP Servers (external tool integrations)")

    # Check npx availability
    has_npx = shutil.which("npx") is not None
    if not has_npx:
        console.print(
            "  [yellow]Warning: npx not found. Install Node.js to use MCP servers.[/yellow]"
        )
        console.print("  [dim]https://nodejs.org/[/dim]\n")

    _MCP_PRESETS: dict[str, dict] = {
        "playwright": {
            "label": "Playwright (browser automation)",
            "config": {
                "command": "npx",
                "args": ["@playwright/mcp@latest"],
                "toolTimeout": 60,
            },
            "needs_npx": True,
        },
        "filesystem": {
            "label": "Filesystem (file access outside workspace)",
            "config": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/"],
                "toolTimeout": 30,
            },
            "needs_npx": True,
        },
        "github": {
            "label": "GitHub (repos, issues, PRs)",
            "config": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": ""},
                "toolTimeout": 30,
            },
            "needs_npx": True,
            "env_prompt": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": "GitHub personal access token",
            },
        },
        "slack": {
            "label": "Slack (messages, channels)",
            "config": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-slack"],
                "env": {"SLACK_BOT_TOKEN": ""},
                "toolTimeout": 30,
            },
            "needs_npx": True,
            "env_prompt": {
                "SLACK_BOT_TOKEN": "Slack bot token (xoxb-...)",
            },
        },
    }

    existing_mcp = config.tools.mcp_servers or {}
    console.print("  Select MCP servers to enable:\n")

    for key, preset in _MCP_PRESETS.items():
        already_configured = key in existing_mcp
        suffix = ""
        if preset.get("needs_npx") and not has_npx:
            suffix = " [yellow](needs npx)[/yellow]"
        if already_configured:
            suffix += " [green](configured)[/green]"

        if typer.confirm(f"  {preset['label']}{suffix}?", default=already_configured):
            if already_configured:
                # Keep existing config (user may have customized it)
                pass
            else:
                from companio.config.schema import MCPServerConfig

                mcp_data = dict(preset["config"])

                # Prompt for required env vars
                env_prompts = preset.get("env_prompt", {})
                if env_prompts:
                    env = dict(mcp_data.get("env", {}))
                    for env_key, env_label in env_prompts.items():
                        val = typer.prompt(
                            f"    {env_label}",
                            default=env.get(env_key, ""),
                            show_default=False,
                        )
                        if val:
                            env[env_key] = val
                    mcp_data["env"] = env

                existing_mcp[key] = MCPServerConfig.model_validate(mcp_data)
        else:
            # Remove if user unchecked
            existing_mcp.pop(key, None)

    config.tools.mcp_servers = existing_mcp
    console.print("\n  [dim]Additional MCP servers can be added manually in config.json[/dim]")

    # --- Save config ---
    save_config(config)
    console.print(f"\n[green]✓[/green] Config saved to {config_path}")

    # Create workspace
    workspace = config.workspace_path
    if not workspace.exists():
        workspace.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓[/green] Created workspace at {workspace}")

    sync_workspace_templates(workspace)

    # Done
    console.print(f"\n{__logo__} [bold green]companio is ready![/bold green]")
    console.print(f"\n  Config: [cyan]{config_path}[/cyan]")
    console.print(f"  Workspace: [cyan]{workspace}[/cyan]")

    if config.channels.telegram.enabled:
        console.print('\n  Start gateway: [cyan]companio gateway[/cyan]')
    console.print('  Chat: [cyan]companio agent -m "Hello!"[/cyan]')


def _make_provider(config: Config):
    """Create the appropriate LLM provider from config."""
    from companio.providers.litellm import LiteLLMProvider
    from companio.providers.registry import find_by_name

    model = config.agents.defaults.model
    provider_name = config.get_provider_name(model)
    p = config.get_provider(model)

    spec = find_by_name(provider_name)
    if not (p and p.api_key) and not (spec and spec.is_oauth):
        console.print("[red]Error: No API key configured.[/red]")
        console.print("Set one in ~/.companio/config.json under providers section")
        raise typer.Exit(1)

    return LiteLLMProvider(
        api_key=p.api_key if p else None,
        api_base=config.get_api_base(model),
        default_model=model,
        extra_headers=p.extra_headers if p else None,
        provider_name=provider_name,
    )


def _load_runtime_config(config: str | None = None, workspace: str | None = None) -> Config:
    """Load config and optionally override the active workspace."""
    from companio.config.loader import load_config, set_config_path

    config_path = None
    if config:
        config_path = Path(config).expanduser().resolve()
        if not config_path.exists():
            console.print(f"[red]Error: Config file not found: {config_path}[/red]")
            raise typer.Exit(1)
        set_config_path(config_path)
        console.print(f"[dim]Using config: {config_path}[/dim]")

    loaded = load_config(config_path)
    if workspace:
        loaded.agents.defaults.workspace = workspace
    return loaded


# ============================================================================
# Gateway / Server
# ============================================================================


@app.command()
def gateway(
    port: int = typer.Option(18790, "--port", "-p", help="Gateway port"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    config: str | None = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Start the companio gateway."""
    from companio.core.loop import AgentLoop
    from companio.bus import MessageBus
    from companio.channels.manager import ChannelManager
    from companio.config.paths import get_cron_dir
    from companio.cron import CronJob, CronService
    from companio.heartbeat import HeartbeatService
    from companio.session import SessionManager

    if verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG)

    config = _load_runtime_config(config, workspace)

    console.print(f"{__logo__} Starting companio gateway on port {port}...")
    sync_workspace_templates(config.workspace_path)
    bus = MessageBus()
    provider = _make_provider(config)
    session_manager = SessionManager(config.workspace_path)

    # Create cron service first (callback set after agent creation)
    cron_store_path = get_cron_dir() / "jobs.json"
    cron = CronService(cron_store_path)

    # Create agent with cron service
    agent = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=config.workspace_path,
        model=config.agents.defaults.model,
        temperature=config.agents.defaults.temperature,
        max_tokens=config.agents.defaults.max_tokens,
        max_iterations=config.agents.defaults.max_tool_iterations,
        memory_window=config.agents.defaults.memory_window,
        reasoning_effort=config.agents.defaults.reasoning_effort,
        brave_api_key=config.tools.web.search.api_key or None,
        web_proxy=config.tools.web.proxy or None,
        exec_config=config.tools.exec,
        cron_service=cron,
        restrict_to_workspace=config.tools.restrict_to_workspace,
        obsidian_vault_path=config.tools.obsidian.vault_path if config.tools.obsidian.enabled else None,
        session_manager=session_manager,
        mcp_servers=config.tools.mcp_servers,
        channels_config=config.channels,
    )

    # Set cron callback (needs agent)
    async def on_cron_job(job: CronJob) -> str | None:
        """Execute a cron job through the agent."""
        from companio.tools.cron_tool import CronTool
        from companio.tools.message import MessageTool

        reminder_note = (
            "[Scheduled Task] Timer finished.\n\n"
            f"Task '{job.name}' has been triggered.\n"
            f"Scheduled instruction: {job.payload.message}"
        )

        # Prevent the agent from scheduling new cron jobs during execution
        cron_tool = agent.tools.get("cron")
        cron_token = None
        if isinstance(cron_tool, CronTool):
            cron_token = cron_tool.set_cron_context(True)
        try:
            response = await agent.process_direct(
                reminder_note,
                session_key=f"cron:{job.id}",
                channel=job.payload.channel or "cli",
                chat_id=job.payload.to or "direct",
            )
        finally:
            if isinstance(cron_tool, CronTool) and cron_token is not None:
                cron_tool.reset_cron_context(cron_token)

        message_tool = agent.tools.get("message")
        if isinstance(message_tool, MessageTool) and message_tool._sent_in_turn:
            return response

        if job.payload.deliver and job.payload.to and response:
            from companio.bus import OutboundMessage

            await bus.publish_outbound(
                OutboundMessage(
                    channel=job.payload.channel or "cli", chat_id=job.payload.to, content=response
                )
            )
        return response

    cron.on_job = on_cron_job

    # Create channel manager
    channels = ChannelManager(config, bus)

    def _pick_heartbeat_target() -> tuple[str, str]:
        """Pick a routable channel/chat target for heartbeat-triggered messages."""
        enabled = set(channels.enabled_channels)
        # Prefer the most recently updated non-internal session on an enabled channel.
        for item in session_manager.list_sessions():
            key = item.get("key") or ""
            if ":" not in key:
                continue
            channel, chat_id = key.split(":", 1)
            if channel in {"cli", "system"}:
                continue
            if channel in enabled and chat_id:
                return channel, chat_id
        # Fallback keeps prior behavior but remains explicit.
        return "cli", "direct"

    # Create heartbeat service
    async def on_heartbeat_execute(tasks: str) -> str:
        """Phase 2: execute heartbeat tasks through the full agent loop."""
        channel, chat_id = _pick_heartbeat_target()

        async def _silent(*_args, **_kwargs):
            pass

        return await agent.process_direct(
            tasks,
            session_key="heartbeat",
            channel=channel,
            chat_id=chat_id,
            on_progress=_silent,
        )

    async def on_heartbeat_notify(response: str) -> None:
        """Deliver a heartbeat response to the user's channel."""
        from companio.bus import OutboundMessage

        channel, chat_id = _pick_heartbeat_target()
        if channel == "cli":
            return  # No external channel available to deliver to
        await bus.publish_outbound(
            OutboundMessage(channel=channel, chat_id=chat_id, content=response)
        )

    hb_cfg = config.gateway.heartbeat
    heartbeat = HeartbeatService(
        workspace=config.workspace_path,
        provider=provider,
        model=agent.model,
        on_execute=on_heartbeat_execute,
        on_notify=on_heartbeat_notify,
        interval_s=hb_cfg.interval_s,
        enabled=hb_cfg.enabled,
    )

    if channels.enabled_channels:
        console.print(f"[green]✓[/green] Channels enabled: {', '.join(channels.enabled_channels)}")
    else:
        console.print("[yellow]Warning: No channels enabled[/yellow]")

    cron_status = cron.status()
    if cron_status["jobs"] > 0:
        console.print(f"[green]✓[/green] Cron: {cron_status['jobs']} scheduled jobs")

    console.print(f"[green]✓[/green] Heartbeat: every {hb_cfg.interval_s}s")

    async def run():
        try:
            await cron.start()
            await heartbeat.start()
            await asyncio.gather(
                agent.run(),
                channels.start_all(),
            )
        except KeyboardInterrupt:
            console.print("\nShutting down...")
        finally:
            await agent.close_mcp()
            heartbeat.stop()
            cron.stop()
            agent.stop()
            await channels.stop_all()

    asyncio.run(run())


# ============================================================================
# Agent Commands
# ============================================================================


@app.command()
def agent(
    message: str = typer.Option(None, "--message", "-m", help="Message to send to the agent"),
    session_id: str = typer.Option("cli:direct", "--session", "-s", help="Session ID"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace directory"),
    config: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
    markdown: bool = typer.Option(
        True, "--markdown/--no-markdown", help="Render assistant output as Markdown"
    ),
    logs: bool = typer.Option(
        False, "--logs/--no-logs", help="Show companio runtime logs during chat"
    ),
):
    """Interact with the agent directly."""
    from loguru import logger

    from companio.core.loop import AgentLoop
    from companio.bus import MessageBus
    from companio.config.paths import get_cron_dir
    from companio.cron import CronService

    config = _load_runtime_config(config, workspace)
    sync_workspace_templates(config.workspace_path)

    bus = MessageBus()
    provider = _make_provider(config)

    # Create cron service for tool usage (no callback needed for CLI unless running)
    cron_store_path = get_cron_dir() / "jobs.json"
    cron = CronService(cron_store_path)

    if logs:
        logger.enable("companio")
    else:
        logger.disable("companio")

    agent_loop = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=config.workspace_path,
        model=config.agents.defaults.model,
        temperature=config.agents.defaults.temperature,
        max_tokens=config.agents.defaults.max_tokens,
        max_iterations=config.agents.defaults.max_tool_iterations,
        memory_window=config.agents.defaults.memory_window,
        reasoning_effort=config.agents.defaults.reasoning_effort,
        brave_api_key=config.tools.web.search.api_key or None,
        web_proxy=config.tools.web.proxy or None,
        exec_config=config.tools.exec,
        cron_service=cron,
        restrict_to_workspace=config.tools.restrict_to_workspace,
        obsidian_vault_path=config.tools.obsidian.vault_path if config.tools.obsidian.enabled else None,
        mcp_servers=config.tools.mcp_servers,
        channels_config=config.channels,
    )

    # Show spinner when logs are off (no output to miss); skip when logs are on
    def _thinking_ctx():
        if logs:
            from contextlib import nullcontext

            return nullcontext()
        # Animated spinner is safe to use with prompt_toolkit input handling
        return console.status("[dim]companio is thinking...[/dim]", spinner="dots")

    async def _cli_progress(content: str, *, tool_hint: bool = False) -> None:
        ch = agent_loop.channels_config
        if ch and tool_hint and not ch.send_tool_hints:
            return
        if ch and not tool_hint and not ch.send_progress:
            return
        console.print(f"  [dim]↳ {content}[/dim]")

    if message:
        # Single message mode -- direct call, no bus needed
        async def run_once():
            with _thinking_ctx():
                response = await agent_loop.process_direct(
                    message, session_id, on_progress=_cli_progress
                )
            _print_agent_response(response, render_markdown=markdown)
            await agent_loop.close_mcp()

        asyncio.run(run_once())
    else:
        # Interactive mode -- route through bus like other channels
        from companio.bus import InboundMessage

        _init_prompt_session()
        console.print(
            f"{__logo__} Interactive mode (type [bold]exit[/bold] or [bold]Ctrl+C[/bold] to quit)\n"
        )

        if ":" in session_id:
            cli_channel, cli_chat_id = session_id.split(":", 1)
        else:
            cli_channel, cli_chat_id = "cli", session_id

        def _handle_signal(signum, frame):
            sig_name = signal.Signals(signum).name
            _restore_terminal()
            console.print(f"\nReceived {sig_name}, goodbye!")
            sys.exit(0)

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)
        # SIGHUP is not available on Windows
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, _handle_signal)
        # Ignore SIGPIPE to prevent silent process termination when writing to closed pipes
        # SIGPIPE is not available on Windows
        if hasattr(signal, "SIGPIPE"):
            signal.signal(signal.SIGPIPE, signal.SIG_IGN)

        async def run_interactive():
            bus_task = asyncio.create_task(agent_loop.run())
            turn_done = asyncio.Event()
            turn_done.set()
            turn_response: list[str] = []

            async def _consume_outbound():
                while True:
                    try:
                        msg = await asyncio.wait_for(bus.consume_outbound(), timeout=1.0)
                        if msg.metadata.get("_progress"):
                            is_tool_hint = msg.metadata.get("_tool_hint", False)
                            ch = agent_loop.channels_config
                            if ch and is_tool_hint and not ch.send_tool_hints:
                                pass
                            elif ch and not is_tool_hint and not ch.send_progress:
                                pass
                            else:
                                console.print(f"  [dim]↳ {msg.content}[/dim]")
                        elif not turn_done.is_set():
                            if msg.content:
                                turn_response.append(msg.content)
                            turn_done.set()
                        elif msg.content:
                            console.print()
                            _print_agent_response(msg.content, render_markdown=markdown)
                    except asyncio.TimeoutError:
                        continue
                    except asyncio.CancelledError:
                        break

            outbound_task = asyncio.create_task(_consume_outbound())

            try:
                while True:
                    try:
                        _flush_pending_tty_input()
                        user_input = await _read_interactive_input_async()
                        command = user_input.strip()
                        if not command:
                            continue

                        if _is_exit_command(command):
                            _restore_terminal()
                            console.print("\nGoodbye!")
                            break

                        turn_done.clear()
                        turn_response.clear()

                        await bus.publish_inbound(
                            InboundMessage(
                                channel=cli_channel,
                                sender_id="user",
                                chat_id=cli_chat_id,
                                content=user_input,
                            )
                        )

                        with _thinking_ctx():
                            await turn_done.wait()

                        if turn_response:
                            _print_agent_response(turn_response[0], render_markdown=markdown)
                    except KeyboardInterrupt:
                        _restore_terminal()
                        console.print("\nGoodbye!")
                        break
                    except EOFError:
                        _restore_terminal()
                        console.print("\nGoodbye!")
                        break
            finally:
                agent_loop.stop()
                outbound_task.cancel()
                await asyncio.gather(bus_task, outbound_task, return_exceptions=True)
                await agent_loop.close_mcp()

        asyncio.run(run_interactive())


# ============================================================================
# Channel Commands
# ============================================================================


channels_app = typer.Typer(help="Manage channels")
app.add_typer(channels_app, name="channels")


@channels_app.command("status")
def channels_status():
    """Show channel status."""
    from companio.config.loader import load_config

    config = load_config()

    table = Table(title="Channel Status")
    table.add_column("Channel", style="cyan")
    table.add_column("Enabled", style="green")
    table.add_column("Configuration", style="yellow")

    # Telegram
    tg = config.channels.telegram
    tg_config = f"token: {tg.token[:10]}..." if tg.token else "[dim]not configured[/dim]"
    table.add_row("Telegram", "✓" if tg.enabled else "✗", tg_config)

    console.print(table)


# ============================================================================
# Status Commands
# ============================================================================


@app.command()
def status():
    """Show companio status."""
    from companio.config.loader import get_config_path, load_config

    config_path = get_config_path()
    config = load_config()
    workspace = config.workspace_path

    console.print(f"{__logo__} companio Status\n")

    console.print(
        f"Config: {config_path} {'[green]✓[/green]' if config_path.exists() else '[red]✗[/red]'}"
    )
    console.print(
        f"Workspace: {workspace} {'[green]✓[/green]' if workspace.exists() else '[red]✗[/red]'}"
    )

    if config_path.exists():
        from companio.providers.registry import PROVIDERS

        console.print(f"Model: {config.agents.defaults.model}")

        # Check API keys from registry
        for spec in PROVIDERS:
            p = getattr(config.providers, spec.name, None)
            if p is None:
                continue
            if spec.is_oauth:
                console.print(f"{spec.label}: [green]✓ (OAuth)[/green]")
            elif spec.is_local:
                # Local deployments show api_base instead of api_key
                if p.api_base:
                    console.print(f"{spec.label}: [green]✓ {p.api_base}[/green]")
                else:
                    console.print(f"{spec.label}: [dim]not set[/dim]")
            else:
                has_key = bool(p.api_key)
                console.print(
                    f"{spec.label}: {'[green]✓[/green]' if has_key else '[dim]not set[/dim]'}"
                )


if __name__ == "__main__":
    app()
