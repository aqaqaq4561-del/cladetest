"""
자율 멀티 에이전트 시스템 — 메인 진입점

실행:
  python main.py

환경변수:
  ANTHROPIC_API_KEY=sk-ant-...
"""

import asyncio
import os
import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.rule import Rule
from rich.text import Text

from agents.team_leader import TeamLeader

console = Console()


def _banner():
    console.print()
    console.print(Panel.fit(
        Text.from_markup(
            "[bold cyan]🤖 자율 멀티 에이전트 시스템[/bold cyan]\n\n"
            "[white]나 → 팀리더 → 팀원 4명 → 심부름꾼 최대 30명 (병렬)[/white]\n"
            "[dim]Phase 1: 리서치  │  Phase 2: 구현[/dim]"
        ),
        border_style="cyan",
    ))
    console.print()


def _section(title: str, emoji: str = ""):
    console.print()
    console.print(Rule(f"{emoji}  {title}  {emoji}", style="bold yellow"))
    console.print()


def _print_proposal(index: int, content: str):
    colors = ["cyan", "magenta", "green"]
    color  = colors[index % len(colors)]
    console.print(Panel(
        content,
        title=f"[bold {color}]제안서 {index + 1}[/bold {color}]",
        border_style=color,
        padding=(1, 2),
    ))
    console.print()


async def main():
    _banner()

    # ── 환경 변수 확인 ──────────────────────────────────────────────────────
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[bold red]❌ 오류: ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.[/bold red]")
        console.print("[dim]export ANTHROPIC_API_KEY=sk-ant-...[/dim]")
        sys.exit(1)

    # ── 태스크 입력 ─────────────────────────────────────────────────────────
    task = Prompt.ask("[bold]💼 어떤 작업을 원하십니까?[/bold]")
    if not task.strip():
        console.print("[red]태스크를 입력해주세요.[/red]")
        sys.exit(1)

    leader = TeamLeader()

    # ══════════════════════════════════════════════════════════════════════════
    # Phase 1: 리서치
    # ══════════════════════════════════════════════════════════════════════════
    _section("Phase 1: 리서치 가동", "📊")
    console.print(f"[dim]태스크: {task}[/dim]\n")

    t0 = time.perf_counter()
    proposals = await leader.research_phase(task)
    elapsed = time.perf_counter() - t0

    console.print(f"\n[green]✅ 리서치 완료 ({elapsed:.1f}초)[/green]")

    # ── 3가지 제안서 출력 ──────────────────────────────────────────────────
    _section("팀리더 보고: 3가지 제안서", "📋")
    for i, proposal in enumerate(proposals):
        _print_proposal(i, proposal)

    # ── 사용자 승인 ────────────────────────────────────────────────────────
    choice = IntPrompt.ask(
        "[bold yellow]✋ 가장 좋은 제안서를 선택하세요[/bold yellow]",
        choices=["1", "2", "3"],
    )
    approved = proposals[choice - 1]
    console.print(f"\n[bold green]✅ 제안서 {choice} 승인됨[/bold green]")

    # ══════════════════════════════════════════════════════════════════════════
    # Phase 2: 구현
    # ══════════════════════════════════════════════════════════════════════════
    _section("Phase 2: 구현 팀 가동", "⚙️")
    console.print("[dim]기존 팀원 전원 해고 → 새 팀원 4명 채용 완료[/dim]\n")

    t0 = time.perf_counter()
    final_report = await leader.implementation_phase(task, approved)
    elapsed = time.perf_counter() - t0

    console.print(f"\n[green]✅ 구현 완료 ({elapsed:.1f}초)[/green]")

    # ── 최종 보고 출력 ──────────────────────────────────────────────────────
    _section("팀리더 최종 보고", "🎯")
    console.print(Panel(
        final_report,
        title="[bold green]최종 보고서[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))

    console.print("\n[bold cyan]🏁 모든 작업 완료![/bold cyan]\n")


if __name__ == "__main__":
    asyncio.run(main())
