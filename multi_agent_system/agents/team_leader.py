"""
팀리더 에이전트 (TeamLeader)

전체 워크플로우 오케스트레이터.
claude-opus-4-6 + adaptive thinking 사용.

Phase 1 (리서치):
  1. 태스크를 분석하여 리서치 계획 수립
  2. 4명 리서치 팀원에게 서브태스크 분배
  3. [병렬] 팀원들이 심부름꾼 실행 (최대 32개 동시)
  4. [병렬] 팀원 초기 합성 포스트
  5. [병렬] 팀원 크로스 리뷰 (실시간 토론)
  6. [병렬] 팀원 최종 보고서 제출
  7. 보고서 종합 → 3가지 제안서 작성

Phase 2 (구현):
  1. 기존 팀 해고, 새 팀원 4명 구성
  2. 승인된 제안서로 구현 계획 수립
  3. [병렬] 새 팀원들이 심부름꾼 실행 (최대 32개 동시)
  4. [병렬] 팀원 검토 및 보고서 제출
  5. 구현물 최종 검토 → 최종 보고
"""

import asyncio
import json
import re
from typing import Dict, List, Tuple

from config import (
    TEAM_LEADER_MODEL, LEADER_MAX_TOKENS,
    RESEARCH_SPECIALTIES, IMPL_SPECIALTIES,
    MIN_RUNNERS, MAX_RUNNERS,
)
from core.client import client
from core.bulletin_board import BulletinBoard
from agents.research_team import ResearchMember
from agents.impl_team import ImplMember


class TeamLeader:

    # ══════════════════════════════════════════════════════════════════════════
    # Phase 1: 리서치
    # ══════════════════════════════════════════════════════════════════════════

    async def research_phase(self, task: str) -> List[str]:
        """리서치 전체 파이프라인 → 3가지 제안서 반환"""

        # ── 리서치 계획 수립 ──
        plan = await self._create_research_plan(task)
        assignments = self._make_research_assignments(plan)

        # ── 새 게시판 생성 (세션 격리) ──
        bb = BulletinBoard("Research")

        # ── 4명 리서치 팀원 생성 ──
        members = [
            ResearchMember(f"RM-{i+1}", sp, bb)
            for i, sp in enumerate(RESEARCH_SPECIALTIES)
        ]

        total_runners = sum(a[1] for a in assignments)
        _log(f"팀리더 → 팀원 {len(members)}명 + 심부름꾼 최대 {total_runners}명 병렬 가동!")

        # ── Step A: 모든 심부름꾼 병렬 실행 ──────────────────────────────────
        _log("Step A │ 심부름꾼 병렬 리서치 시작...")
        runner_tasks = [
            member.run_runners(task, subtasks, num_runners)
            for member, (subtasks, num_runners) in zip(members, assignments)
        ]
        all_results = await asyncio.gather(*runner_tasks)
        _log(f"Step A │ 완료 — 총 {sum(len(r) for r in all_results)}건 리서치 수집")

        # ── Step B: 팀원 초기 합성 (병렬) ───────────────────────────────────
        _log("Step B │ 팀원 초기 합성 포스트 중...")
        synthesis_tasks = [
            member.post_initial_synthesis(task, assignments[i][0], all_results[i])
            for i, member in enumerate(members)
        ]
        await asyncio.gather(*synthesis_tasks)
        _log("Step B │ 4명 초기 합성 완료")

        # ── Step C: 크로스 리뷰 / 실시간 토론 (병렬) ────────────────────────
        _log("Step C │ 팀원 크로스 리뷰 (실시간 토론) 중...")
        review_tasks = [member.post_cross_review(task) for member in members]
        await asyncio.gather(*review_tasks)
        _log("Step C │ 2라운드 토론 완료")

        # ── Step D: 최종 보고서 제출 (병렬) ─────────────────────────────────
        _log("Step D │ 팀원 최종 보고서 제출 중...")
        report_tasks = [member.submit_final_report(task) for member in members]
        await asyncio.gather(*report_tasks)
        _log("Step D │ 4명 보고서 모두 수신")

        # ── Step E: 팀리더가 3가지 제안서 작성 ──────────────────────────────
        _log("Step E │ 팀리더 종합 → 3가지 제안서 작성...")
        reports = await bb.get_all_final_reports()
        proposals = await self._generate_proposals(task, reports)
        _log("Step E │ 3가지 제안서 완성")

        return proposals

    # ══════════════════════════════════════════════════════════════════════════
    # Phase 2: 구현
    # ══════════════════════════════════════════════════════════════════════════

    async def implementation_phase(self, task: str, approved_proposal: str) -> str:
        """구현 전체 파이프라인 → 최종 보고서 반환"""

        _log("기존 팀 해고 ✓  │  새 구현 팀원 4명 채용...")

        # ── 구현 계획 수립 ──
        plan = await self._create_impl_plan(task, approved_proposal)
        assignments = self._make_impl_assignments(plan)

        # ── 새 게시판 생성 (완전히 새 팀) ──
        bb = BulletinBoard("Implementation")

        # ── 4명 구현 팀원 생성 ──
        members = [
            ImplMember(f"IM-{i+1}", sp, bb)
            for i, sp in enumerate(IMPL_SPECIALTIES)
        ]

        total_runners = sum(a[1] for a in assignments)
        _log(f"팀리더 → 새 팀원 {len(members)}명 + 심부름꾼 최대 {total_runners}명 병렬 구현 가동!")

        context = f"## 승인된 제안서\n{approved_proposal}"

        # ── Step A: 모든 구현 심부름꾼 병렬 실행 ────────────────────────────
        _log("Step A │ 심부름꾼 병렬 구현 시작...")
        runner_tasks = [
            member.run_runners(task, subtasks, num_runners, context)
            for member, (subtasks, num_runners) in zip(members, assignments)
        ]
        all_results = await asyncio.gather(*runner_tasks)
        _log(f"Step A │ 완료 — 총 {sum(len(r) for r in all_results)}건 구현 완료")

        # ── Step B: 팀원 검토 및 보고서 제출 (병렬) ─────────────────────────
        _log("Step B │ 팀원 검토 및 보고서 제출 중...")
        review_tasks = [
            member.review_and_submit(task, assignments[i][0], all_results[i], approved_proposal)
            for i, member in enumerate(members)
        ]
        await asyncio.gather(*review_tasks)
        _log("Step B │ 4명 구현 보고서 모두 수신")

        # ── Step C: 팀리더 최종 검토 ─────────────────────────────────────────
        _log("Step C │ 팀리더 최종 검토 및 보고 작성...")
        reports = await bb.get_all_final_reports()
        final = await self._final_review(task, approved_proposal, reports)
        _log("Step C │ 최종 보고서 완성")

        return final

    # ══════════════════════════════════════════════════════════════════════════
    # 내부 헬퍼: 계획 수립
    # ══════════════════════════════════════════════════════════════════════════

    async def _create_research_plan(self, task: str) -> Dict:
        """4개 전문 분야별 리서치 서브태스크 목록을 JSON으로 생성"""
        response = await client.messages.create(
            model=TEAM_LEADER_MODEL,
            max_tokens=3000,
            thinking={"type": "adaptive"},
            system=(
                "당신은 전략적 팀리더입니다.\n"
                "주어진 태스크를 분석하여 4개 전문 분야별 리서치 계획을 JSON으로 수립합니다."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"태스크: {task}\n\n"
                    "아래 4개 분야별로 리서치 서브태스크를 JSON으로 작성해주세요 "
                    "(각 분야 3~8개 서브태스크):\n\n"
                    "```json\n"
                    "{\n"
                    '  "market":      ["서브태스크1", "서브태스크2", ...],\n'
                    '  "tech":        ["서브태스크1", ...],\n'
                    '  "competitive": ["서브태스크1", ...],\n'
                    '  "risk":        ["서브태스크1", ...]\n'
                    "}\n"
                    "```\n"
                    "JSON만 출력하세요."
                ),
            }],
        )
        return _parse_json(response, {
            "market":      ["시장 규모 및 트렌드 분석"],
            "tech":        ["기술 실현 가능성 검토"],
            "competitive": ["경쟁사 현황 분석"],
            "risk":        ["주요 리스크 식별"],
        })

    async def _create_impl_plan(self, task: str, proposal: str) -> Dict:
        """4개 구현 분야별 서브태스크 목록을 JSON으로 생성"""
        response = await client.messages.create(
            model=TEAM_LEADER_MODEL,
            max_tokens=4000,
            thinking={"type": "adaptive"},
            system=(
                "당신은 기술 팀리더입니다.\n"
                "승인된 제안서를 기반으로 실제 구현 계획을 4개 분야별 JSON으로 수립합니다."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"태스크: {task}\n\n"
                    f"승인된 제안서:\n{proposal}\n\n"
                    "아래 4개 분야별 구현 서브태스크를 JSON으로 작성해주세요 "
                    "(각 분야 3~8개):\n\n"
                    "```json\n"
                    "{\n"
                    '  "architecture": ["설계 태스크1", ...],\n'
                    '  "core":         ["핵심 구현 태스크1", ...],\n'
                    '  "quality":      ["테스트 태스크1", ...],\n'
                    '  "deployment":   ["배포 태스크1", ...]\n'
                    "}\n"
                    "```\n"
                    "JSON만 출력하세요."
                ),
            }],
        )
        return _parse_json(response, {
            "architecture": ["시스템 아키텍처 설계"],
            "core":         ["핵심 기능 구현"],
            "quality":      ["테스트 케이스 작성"],
            "deployment":   ["배포 파이프라인 구성"],
        })

    # ══════════════════════════════════════════════════════════════════════════
    # 내부 헬퍼: 태스크 분배
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _make_research_assignments(plan: Dict) -> List[Tuple[List[str], int]]:
        areas = ["market", "tech", "competitive", "risk"]
        defaults = [
            ["시장 분석"],
            ["기술 검토"],
            ["경쟁사 분석"],
            ["리스크 분석"],
        ]
        result = []
        for i, area in enumerate(areas):
            subtasks    = plan.get(area, defaults[i])
            num_runners = max(MIN_RUNNERS, min(MAX_RUNNERS, len(subtasks)))
            result.append((subtasks, num_runners))
        return result

    @staticmethod
    def _make_impl_assignments(plan: Dict) -> List[Tuple[List[str], int]]:
        areas = ["architecture", "core", "quality", "deployment"]
        defaults = [
            ["아키텍처 설계"],
            ["핵심 구현"],
            ["테스트"],
            ["배포"],
        ]
        result = []
        for i, area in enumerate(areas):
            subtasks    = plan.get(area, defaults[i])
            num_runners = max(MIN_RUNNERS, min(MAX_RUNNERS, len(subtasks)))
            result.append((subtasks, num_runners))
        return result

    # ══════════════════════════════════════════════════════════════════════════
    # 내부 헬퍼: 제안서 / 최종 보고서 생성
    # ══════════════════════════════════════════════════════════════════════════

    async def _generate_proposals(
        self, task: str, reports: Dict[str, str]
    ) -> List[str]:
        """팀원 보고서를 종합하여 3가지 차별화된 제안서 생성"""
        reports_text = "\n\n---\n\n".join(
            f"### [{mid}] 보고서\n{rpt}"
            for mid, rpt in reports.items()
        )

        response = await client.messages.create(
            model=TEAM_LEADER_MODEL,
            max_tokens=LEADER_MAX_TOKENS,
            thinking={"type": "adaptive"},
            system=(
                "당신은 전략적 팀리더입니다.\n"
                "팀원 보고서를 종합하여 의뢰인에게 3가지 차별화된 전략적 제안서를 작성합니다.\n"
                "각 제안서는 서로 다른 접근 방식을 제시해야 합니다."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"프로젝트 태스크: {task}\n\n"
                    f"팀원 보고서:\n{reports_text}\n\n"
                    "아래 형식으로 3가지 제안서를 작성하세요:\n\n"
                    "## 제안서 1: [제목] (안정적 접근)\n"
                    "- **핵심 전략**: ...\n"
                    "- **접근 방식**: ...\n"
                    "- **예상 결과**: ...\n"
                    "- **장단점**: ...\n"
                    "- **실행 로드맵**: ...\n\n"
                    "## 제안서 2: [제목] (균형 접근)\n"
                    "...\n\n"
                    "## 제안서 3: [제목] (혁신적 접근)\n"
                    "..."
                ),
            }],
        )

        text = next(b.text for b in response.content if b.type == "text")
        return _split_proposals(text)

    async def _final_review(
        self, task: str, proposal: str, reports: Dict[str, str]
    ) -> str:
        """구현 보고서를 최종 검토하여 의뢰인에게 보고"""
        reports_text = "\n\n---\n\n".join(
            f"### [{mid}] 구현 보고\n{rpt}"
            for mid, rpt in reports.items()
        )

        response = await client.messages.create(
            model=TEAM_LEADER_MODEL,
            max_tokens=LEADER_MAX_TOKENS,
            thinking={"type": "adaptive"},
            system=(
                "당신은 기술 팀리더입니다.\n"
                "팀원들의 구현 보고서를 최종 검토하고 의뢰인에게 완성된 결과물을 보고합니다."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"프로젝트 태스크: {task}\n\n"
                    f"승인된 제안서:\n{proposal[:1500]}\n\n"
                    f"팀원 구현 보고서:\n{reports_text}\n\n"
                    "의뢰인에게 제출할 최종 보고서를 작성하세요:\n"
                    "1. **프로젝트 완료 요약**\n"
                    "2. **핵심 결과물 목록** (구체적 열거)\n"
                    "3. **품질 검토 결과**\n"
                    "4. **즉시 활용 가능한 산출물**\n"
                    "5. **다음 단계 권고사항**"
                ),
            }],
        )

        return next(b.text for b in response.content if b.type == "text")


# ── 유틸리티 ──────────────────────────────────────────────────────────────────

def _log(msg: str) -> None:
    print(f"  [팀리더] {msg}")


def _parse_json(response, default: Dict) -> Dict:
    text = next(b.text for b in response.content if b.type == "text")
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return default


def _split_proposals(text: str) -> List[str]:
    """'## 제안서 N' 구분자로 텍스트를 3개 제안서로 분리"""
    parts = re.split(r"##\s*제안서\s*[123]", text)
    proposals = [p.strip() for p in parts if p.strip()]
    while len(proposals) < 3:
        proposals.append(f"제안서 {len(proposals)+1}: 기본 전략")
    return proposals[:3]
