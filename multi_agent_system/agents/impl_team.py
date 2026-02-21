"""
구현 팀원 에이전트 (ImplMember)

Phase 2 워크플로우:
  Step A │ 소속 심부름꾼들을 병렬로 실행하여 구현 수행
  Step B │ 심부름꾼 결과물을 검토하고 품질 평가
  Step C │ 최종 구현 보고서를 팀리더에게 제출
"""

import asyncio
from typing import List

from config import TEAM_MEMBER_MODEL, MEMBER_MAX_TOKENS
from core.client import client
from core.bulletin_board import BulletinBoard
from agents.runner import impl_runner


class ImplMember:
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
        context: str,
    ) -> List[str]:
        """Step A: 구현 심부름꾼들을 병렬로 실행"""
        actual = min(num_runners, len(subtasks))
        tasks  = [
            impl_runner(
                runner_id=f"{self.member_id}-I{i+1}",
                member_id=self.member_id,
                main_task=main_task,
                subtask=subtasks[i],
                context=context,
                bb=self.bb,
            )
            for i in range(actual)
        ]
        return await asyncio.gather(*tasks)

    async def review_and_submit(
        self,
        main_task: str,
        subtasks: List[str],
        impl_results: List[str],
        approved_proposal: str,
    ) -> str:
        """Step B+C: 심부름꾼 결과 검토 후 최종 보고서 제출"""
        results_text = "\n\n".join(
            f"**[{self.member_id}-I{i+1}] {t}**\n{r}"
            for i, (t, r) in enumerate(zip(subtasks, impl_results))
        )

        response = await client.messages.create(
            model=TEAM_MEMBER_MODEL,
            max_tokens=MEMBER_MAX_TOKENS,
            system=(
                f"당신은 구현 팀원입니다 (ID: {self.member_id}).\n"
                f"전문 분야: {self.specialty}\n"
                f"전체 프로젝트: {main_task}\n\n"
                "역할:\n"
                "- 심부름꾼들의 구현 결과를 엄격히 검토합니다\n"
                "- 품질·완성도·실용성을 평가합니다\n"
                "- 팀리더에게 제출할 구현 보고서를 작성합니다"
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"승인된 제안서 요약:\n{approved_proposal[:800]}\n\n"
                    f"심부름꾼 구현 결과:\n{results_text}\n\n"
                    "아래 구조로 팀리더에게 제출할 구현 보고서를 작성하세요:\n"
                    "1. **구현 완료 항목 목록** (체크리스트 형식)\n"
                    "2. **핵심 결과물** (코드·설계·문서 요약)\n"
                    "3. **품질 검토 결과** (완성도, 이슈, 개선점)\n"
                    "4. **통합 시 고려사항**"
                ),
            }],
        )

        report = next(b.text for b in response.content if b.type == "text")
        await self.bb.submit_final_report(self.member_id, report)
        return report
