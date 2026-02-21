"""
심부름꾼 에이전트 (Runner)

가장 가벼운 레이어. claude-haiku-4-5 모델을 사용하며,
팀원으로부터 단일 서브태스크를 받아 실행하고 결과를 반환합니다.

- research_runner : 리서치 서브태스크 실행
- impl_runner     : 구현 서브태스크 실행
"""

import asyncio
from config import RUNNER_MODEL, RUNNER_MAX_TOKENS
from core.client import client
from core.bulletin_board import BulletinBoard


async def research_runner(
    runner_id: str,
    member_id: str,
    main_task: str,
    subtask: str,
    bb: BulletinBoard,
) -> str:
    """
    리서치 심부름꾼.
    subtask에 대해 Claude를 호출하여 리서치 결과를 생성하고
    BulletinBoard에 등록한 뒤 내용을 반환합니다.
    """
    response = await client.messages.create(
        model=RUNNER_MODEL,
        max_tokens=RUNNER_MAX_TOKENS,
        system=(
            f"당신은 리서치 심부름꾼입니다 (ID: {runner_id}).\n"
            f"소속 팀원: {member_id}\n"
            f"전체 프로젝트: {main_task}\n\n"
            "역할:\n"
            "- 주어진 서브태스크를 심층 조사합니다\n"
            "- 구체적 사실, 수치, 사례를 포함합니다\n"
            "- 200~400자 분량으로 핵심 내용을 명확히 정리합니다\n"
            "- 마크다운 형식으로 작성합니다"
        ),
        messages=[{
            "role": "user",
            "content": f"리서치 태스크: {subtask}\n\n위 주제를 철저히 조사하여 핵심 인사이트를 보고하세요.",
        }],
    )

    content = next(b.text for b in response.content if b.type == "text")
    await bb.post_runner_result(runner_id, member_id, subtask, content)
    return content


async def impl_runner(
    runner_id: str,
    member_id: str,
    main_task: str,
    subtask: str,
    context: str,
    bb: BulletinBoard,
) -> str:
    """
    구현 심부름꾼.
    subtask에 대한 실제 구현 결과물(코드, 문서, 계획 등)을 생성하고
    BulletinBoard에 등록한 뒤 내용을 반환합니다.
    """
    response = await client.messages.create(
        model=RUNNER_MODEL,
        max_tokens=RUNNER_MAX_TOKENS,
        system=(
            f"당신은 구현 심부름꾼입니다 (ID: {runner_id}).\n"
            f"소속 팀원: {member_id}\n"
            f"전체 프로젝트: {main_task}\n\n"
            "역할:\n"
            "- 주어진 구현 서브태스크를 실제로 수행합니다\n"
            "- 코드, 설계서, 계획서 등 구체적 결과물을 생산합니다\n"
            "- 완성도 높고 실용적인 결과물을 제출합니다\n"
            "- 마크다운 형식으로 작성합니다\n\n"
            f"컨텍스트 (승인된 제안서):\n{context}"
        ),
        messages=[{
            "role": "user",
            "content": f"구현 태스크: {subtask}\n\n위 태스크를 실제로 구현하고 완성된 결과물을 제출하세요.",
        }],
    )

    content = next(b.text for b in response.content if b.type == "text")
    await bb.post_runner_result(runner_id, member_id, subtask, content)
    return content
