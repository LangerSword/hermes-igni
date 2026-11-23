"""Table: card games inside Hermes.

Two deterministic engines (Gwent-style row warfare and an Arena mana duel),
four tools, a `/table` slash command, a `hermes table` CLI, a live TUI
scoreboard and a playable desktop page. The user is the player; the opponent's
hand never leaves the engine.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

__version__ = "0.1.0"

TOOLSET = "table"

SYSTEM_PROMPT = (
    "Card table: table_new starts Gwent (row warfare) or Arena (mana duel); "
    "table_play relays the USER's move. The user is the player — ask for their move, "
    "never choose one for them, and never reveal the opponent's hidden hand. "
    "Render the returned `board` text in a fenced code block."
)


def register(ctx) -> None:
    from .table_cli import handle_cli, handle_slash, setup_cli
    from .table_tools import TOOL_SPECS

    for spec in TOOL_SPECS:
        def tool_handler(args: dict, _run=spec["handler"], **_kw) -> str:
            return _run(args or {})

        ctx.register_tool(
            name=spec["name"],
            toolset=TOOLSET,
            schema=spec["schema"],
            handler=tool_handler,
            description=spec["description"],
            emoji=spec.get("emoji", "🃏"),
        )

    ctx.register_command(
        "table",
        handle_slash,
        description="Show the active card table, its rules, or deal a new one",
        args_hint="[board|rules|new] [gwent|arena] [seed]",
    )

    ctx.register_cli_command(
        "table",
        help="Card games inside Hermes (Gwent / Arena)",
        description=(
            "Show or start a card table, print its rules, run an AI-vs-AI demo, "
            "or play a table in this terminal."
        ),
        setup_fn=setup_cli,
        handler_fn=handle_cli,
    )

    ctx.register_system_prompt_section(
        "table",
        SYSTEM_PROMPT,
        position="after_memory",
        max_chars=420,
    )


__all__ = ["register", "__version__"]
