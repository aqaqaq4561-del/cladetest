"""
게시판 (BulletinBoard) — 에이전트 간 실시간 공유 메모리

팀원들이 서로의 리서치/구현 결과를 읽고 토론할 수 있는
asyncio-safe 공유 상태 저장소입니다.

사용 흐름:
  1. 심부름꾼이 연구 결과를 post_runner_result()로 등록
  2. 팀원이 post_member_synthesis()로 초기 분석 공유
  3. 팀원들이 read_all_syntheses()로 서로의 분석을 읽음
  4. 팀원이 post_discussion_reply()로 의견 교환
  5. 팀원이 submit_final_report()로 최종 보고서 제출
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class RunnerResult:
    runner_id:   str
    member_id:   str
    subtask:     str
    content:     str
    timestamp:   str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DiscussionPost:
    author:      str
    round_num:   int          # 1 = 초기 합성, 2 = 크로스 리뷰
    content:     str
    timestamp:   str = field(default_factory=lambda: datetime.now().isoformat())


class BulletinBoard:
    """asyncio.Lock 으로 보호되는 공유 게시판"""

    def __init__(self, session_name: str = ""):
        self.session_name  = session_name
        self._lock         = asyncio.Lock()

        # 심부름꾼 결과: runner_id → RunnerResult
        self._runner_results: Dict[str, RunnerResult] = {}

        # 팀원 토론: 라운드별 리스트
        self._discussion: List[DiscussionPost] = []

        # 최종 보고서: member_id → str
        self._final_reports: Dict[str, str] = {}

    # ── 심부름꾼 결과 ──────────────────────────────────────────────────────────

    async def post_runner_result(
        self,
        runner_id: str,
        member_id: str,
        subtask: str,
        content: str,
    ) -> None:
        async with self._lock:
            self._runner_results[runner_id] = RunnerResult(
                runner_id=runner_id,
                member_id=member_id,
                subtask=subtask,
                content=content,
            )

    async def get_runner_results_for_member(
        self, member_id: str
    ) -> List[RunnerResult]:
        async with self._lock:
            return [r for r in self._runner_results.values() if r.member_id == member_id]

    async def get_all_runner_results(self) -> List[RunnerResult]:
        async with self._lock:
            return list(self._runner_results.values())

    # ── 팀원 토론 ─────────────────────────────────────────────────────────────

    async def post_discussion(
        self, author: str, round_num: int, content: str
    ) -> None:
        async with self._lock:
            self._discussion.append(
                DiscussionPost(author=author, round_num=round_num, content=content)
            )

    async def get_discussion_round(self, round_num: int) -> List[DiscussionPost]:
        async with self._lock:
            return [p for p in self._discussion if p.round_num == round_num]

    async def get_full_discussion(self) -> List[DiscussionPost]:
        async with self._lock:
            return list(self._discussion)

    # ── 최종 보고서 ───────────────────────────────────────────────────────────

    async def submit_final_report(self, member_id: str, report: str) -> None:
        async with self._lock:
            self._final_reports[member_id] = report

    async def get_all_final_reports(self) -> Dict[str, str]:
        async with self._lock:
            return dict(self._final_reports)

    # ── 상태 요약 ─────────────────────────────────────────────────────────────

    async def summary(self) -> str:
        async with self._lock:
            return (
                f"[{self.session_name}] "
                f"심부름꾼결과={len(self._runner_results)}, "
                f"토론포스트={len(self._discussion)}, "
                f"최종보고서={len(self._final_reports)}"
            )
