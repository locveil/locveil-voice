"""ARCH-15 PR-0 — the InputManager must not auto-start the `cli` source.

The interactive runner (`InteractiveRunnerMixin._run_interactive_loop`) owns stdin via its own
prompt_toolkit reader and calls `process_text_input` directly. If the InputManager *also*
auto-starts the `CLIInput` source, a second prompt_toolkit reader races for the same TTY and the
lines it wins land in a `_command_queue` that nothing drains (`get_next_input` has no live
consumer) — so typed commands are silently dropped. PR-0 stops auto-starting `cli` (the source
stays registered, just not started), mirroring the existing `web` guard.
"""

from irene.config.models import InputConfig
from irene.inputs.manager import InputManager


async def test_cli_source_registered_but_not_auto_started():
    """With cli enabled + default, `cli` is discovered into `_sources` but NOT auto-started."""
    cfg = InputConfig(microphone=False, web=False, cli=True, default_input="cli")
    mgr = InputManager(component_manager=None, input_config=cfg)

    await mgr.initialize()

    # Registered and available — the runner can still reach the handle if it wants it.
    assert "cli" in mgr._sources, "CLI source should still be registered"
    # But NOT started — no competing prompt_toolkit reader on the TTY.
    assert "cli" not in mgr._active_sources, "CLI source must not be auto-started (PR-0)"

    await mgr.close()


async def test_cli_input_loop_not_spawned():
    """The CLIInput background read loop is never created when only cli is configured."""
    cfg = InputConfig(microphone=False, web=False, cli=True, default_input="cli")
    mgr = InputManager(component_manager=None, input_config=cfg)

    await mgr.initialize()

    cli_source = mgr._sources["cli"]
    # CLIInput spawns its prompt_toolkit reader in start_listening(); not auto-started => no task,
    # so it is not listening and there is no second reader competing for stdin.
    assert cli_source.is_listening() is False
    assert "cli" not in mgr._listen_tasks

    await mgr.close()
