"""
리서치 팀원 에이전트 (ResearchMember)

Phase 1 워크플로우:
  Step A │ 소속 심부름꾼들을 병렬로 실행 → 결과를 BulletinBoard에 등록
  Step B │ 자신의 결과를 초기 합성 → 게시판에 Round-1 토론 포스트
  Step C │ 다른 팀원의 Round-1 포스트를 읽고 크로스 리뷰 → Round-2 포스트
  Step D │ 전체 토론을 반영한 최종 보고서를 팀리더에게 제출
"""

import asyncio
from typing import List

from config import TEAM_MEMBER_MODEL, MEMBER_MAX_TOKENS
from core.client import client
from core.bulletin_board import BulletinBoard
from agents.runner import research_runner


class ResearchMember:
    def __init__(self, member_id: str, specialty: str, bb: BulletinBoard):
        self.member_id = member_id
        self.specialty = specialty
        self.bb        = bb

    # ── 공개 진입점 ───────────────────────────────────────────────────────────

    async def run_runners(
        self,
        main_task: str,
        subtasks: List[str],
        num_runners: int,
    ) -> List[str]:
        """Step A: 심부름꾼들을 병렬로 실행하고 결과 리스트를 반환"""
        actual = min(num_runners, len(subtasks))
        tasks  = [
            research_runner(
                runner_id=f"{self.member_id}-R{i+1}",
                member_id=self.member_id,
                main_task=main_task,
                subtask=subtasks[i],
                bb=self.bb,
            )
            for i in range(actual)
        ]
        return await asyncio.gather(*tasks)

    async def post_initial_synthesis(
        self,
        main_task: str,
        subtasks: List[str],
        my_results: List[str],
    ) -> str:
        """Step B: 자신의 심부름꾼 결과를 초기 합성하여 Round-1 게시"""
        results_text = "\n\n".join(
            f"**서브태스크 [{t}]**\n{r}"
            for t, r in zip(subtasks, my_results)
        )

        response = await client.messages.create(
            model=TEAM_MEMBER_MODEL,
            max_tokens=MEMBER_MAX_TOKENS,
            system=(
                f"당신은 리서치 팀원입니다 (ID: {self.member_id}).\n"
                f"전문 분야: {self.specialty}\n"
                f"전체 프로젝트: {main_task}\n\n"
                "역할: 심부름꾼 결과를 종합하여 핵심 인사이트를 팀에 공유합니다."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"내 심부름꾼들의 리서치 결과:\n{results_text}\n\n"
                    "위 결과를 종합하여 팀에게 공유할 초기 분석(300~500자)을 작성하세요.\n"
                    "포함사항: 핵심 발견, 주목할 인사이트, 전문 분야 관점의 평가"
                ),
            }],
        )

        synthesis = next(b.text for b in response.content if b.type == "text")
        await self.bb.post_discussion(self.member_id, round_num=1, content=synthesis)
        return synthesis

    async def post_cross_review(self, main_task: str) -> str:
        """Step C: 다른 팀원의 Round-1 포스트를 읽고 크로스 리뷰 게시"""
        round1_posts = await self.bb.get_discussion_round(1)

        others_text = "\n\n".join(
            f"**[{p.author}]** ({p.timestamp[:16]}):\n{p.content}"
            for p in round1_posts
            if p.author != self.member_id
        )

        my_post = next(
            (p.content for p in round1_posts if p.author == self.member_id), ""
        )

        response = await client.messages.create(
            model=TEAM_MEMBER_MODEL,
            max_tokens=MEMBER_MAX_TOKENS,
            system=(
                f"당신은 리서치 팀원입니다 (ID: {self.member_id}).\n"
                f"전문 분야: {self.specialty}\n\n"
                "역할: 동료들의 분석을 읽고 의견을 교환하는 팀 토론에 참여합니다.\n"
                "건설적인 피드백, 추가 인사이트, 통합 관점을 제시합니다."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"내 초기 분석:\n{my_post}\n\n"
                    f"동료 팀원들의 초기 분석:\n{others_text}\n\n"
                    "동료들의 분석을 검토하고, 공통점·차이점·새로운 인사이트를 포함한 "
                    "크로스 리뷰(200~400자)를 작성하세요."
                ),
            }],
        )

        review = next(b.text for b in response.content if b.type == "text")
        await self.bb.post_discussion(self.member_id, round_num=2, content=review)
        return review

    async def submit_final_report(self, main_task: str) -> str:
        """Step D: 전체 토론을 반영한 최종 보고서 작성 및 제출"""
        all_posts = await self.bb.get_full_discussion()
        discussion_text = "\n\n".join(
            f"**[{p.author} / Round {p.round_num}]**:\n{p.content}"
            for p in all_posts
        )

        response = await client.messages.create(
            model=TEAM_MEMBER_MODEL,
            max_tokens=MEMBER_MAX_TOKENS,
            system=(
                f"당신은 리서치 팀원입니다 (ID: {self.member_id}).\n"
                f"전문 분야: {self.specialty}\n"
                f"전체 프로젝트: {main_task}\n\n"
                "역할: 팀 토론 전체를 반영하여 팀리더에게 제출할 최종 보고서를 작성합니다."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"팀 전체 토론 내용:\n{discussion_text}\n\n"
                    "아래 구조로 최종 보고서를 작성하세요:\n"
                    "1. **핵심 발견사항** (전문 분야 관점)\n"
                    "2. **팀 토론 종합 인사이트**\n"
                    "3. **전략적 권고사항** (3가지 이상)\n"
                    "4. **리스크 및 고려사항**"
                ),
            }],
        )

        report = next(b.text for b in response.content if b.type == "text")
        await self.bb.submit_final_report(self.member_id, report)
        return report
