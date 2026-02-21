"""
공유 Anthropic 비동기 클라이언트
모든 에이전트가 이 단일 클라이언트 인스턴스를 공유합니다.
"""
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

# 전역 공유 async 클라이언트
client = anthropic.AsyncAnthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)
