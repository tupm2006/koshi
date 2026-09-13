import enum
import json
import logging
import re
import httpx
from typing import List, Dict, Any, Optional, Tuple
from app.config import settings

logger = logging.getLogger(__name__)


class AIFeature(str, enum.Enum):
    """
    Which workflow a call belongs to.

    Passed explicitly so the deterministic fallback can select its response by
    identity rather than by sniffing substrings out of the prompt text, which
    meant that rewording a prompt silently changed the fallback (F-10).
    """
    WEEKLY_SUMMARY = "weekly_summary"
    MEETING_MINUTES = "meeting_minutes"
    ASSIGNMENT = "assignment"


class AITier(str, enum.Enum):
    """
    Which tier of the cascade actually produced an answer.

    The cascade is silent by design — every tier returns the same `str`, so a
    deployment whose API key has expired keeps serving canned Vietnamese text
    and looks entirely healthy. That was D5 GAP-04: the tests asserted response
    *shape*, which tier 3 satisfies perfectly, so a total AI outage left the
    suite green.

    Tracking the tier costs nothing at runtime and makes the difference
    assertable. It is deliberately NOT part of any HTTP response — that would
    be a D4 contract change. It exists for tests and for the log line below.
    """
    CLOUD = "cloud"            # tier 1 — configured OpenAI-compatible endpoint
    OLLAMA = "ollama"          # tier 2 — local model
    DETERMINISTIC = "fallback"  # tier 3 — no model was reached at all


class AIService:
    @classmethod
    async def _call_llm(
        cls, feature: "AIFeature", system_prompt: str, user_prompt: str
    ) -> Tuple[str, "AITier"]:
        """
        Executes LLM request with graceful fallback cascade:
        1. Configured OpenAI-compatible endpoint (if key present)
        2. Local Ollama server (http://localhost:11434)
        3. Deterministic heuristic compiler (offline zero-failure guarantee)

        Returns the text *and* the tier that produced it. Callers that only want
        the text should still not discard the tier silently — the point of
        returning it is that falling through to tier 3 is a degradation, not a
        success, even though it never raises.
        """
        # 1. Cloud API, whenever a key is configured. This used to also require
        #    "openai" in the URL, which silently disabled tier 1 for every other
        #    OpenAI-compatible vendor even with a valid key (F-11).
        if settings.AI_API_KEY:
            try:
                headers = {"Authorization": f"Bearer {settings.AI_API_KEY}"}
                payload = {
                    "model": settings.AI_MODEL_NAME,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.2
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    res = await client.post(settings.AI_API_URL, headers=headers, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        return data["choices"][0]["message"]["content"], AITier.CLOUD
                    logger.warning(
                        "AI tier 1 (%s) returned HTTP %s for %s; falling through",
                        settings.AI_API_URL, res.status_code, feature.value,
                    )
            except Exception as exc:
                logger.warning("AI tier 1 failed for %s: %s", feature.value, exc)

        # 2. Try Local Ollama endpoint
        try:
            ollama_payload = {
                "model": settings.OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False
            }
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(settings.OLLAMA_URL, json=ollama_payload)
                if res.status_code == 200:
                    data = res.json()
                    # Ollama answers in its own shape behind /api/chat and in the
                    # OpenAI shape behind /v1/chat/completions; accept both.
                    if "choices" in data:
                        return data["choices"][0]["message"]["content"], AITier.OLLAMA
                    elif "message" in data:
                        return data["message"]["content"], AITier.OLLAMA
        except Exception as exc:
            logger.info("AI tier 2 (ollama) unavailable for %s: %s", feature.value, exc)

        # 3. Deterministic Heuristic Engine Fallback
        logger.warning(
            "AI DEGRADED: no model reached for %s; serving the deterministic "
            "fallback. Output is canned text, not analysis.",
            feature.value,
        )
        return cls._deterministic_fallback(feature, user_prompt), AITier.DETERMINISTIC

    @classmethod
    def _deterministic_fallback(cls, feature: "AIFeature", user_prompt: str) -> str:
        # Meeting Minutes (Feature B)
        if feature is AIFeature.MEETING_MINUTES:
            lines = [l.strip("-•* \t") for l in user_prompt.split("\n") if len(l.strip()) > 5]
            topics = ["Tổng kết tiến độ Sprint", "Phân tích rào cản kỹ thuật", "Thống nhất bàn giao và triển khai"]
            action_items = []
            
            for line in lines:
                if any(kw in line.lower() for kw in ["làm", "xong", "fix", "code", "dev", "test", "deploy", "thiết kế"]):
                    action_items.append({
                        "title": line,
                        "assignee_name": "Phạm Minh Tú" if "tupm" in line.lower() else "Team Dev",
                        "priority": "HIGH" if any(w in line.lower() for w in ["gấp", "trước", "fix", "bug"]) else "MEDIUM",
                        "deadline": "Next Sprint"
                    })
            
            if not action_items:
                action_items.append({
                    "title": "Hoàn thiện các đầu việc tồn đọng từ cuộc họp",
                    "assignee_name": "Toàn đội ngũ",
                    "priority": "HIGH",
                    "deadline": "2 ngày tới"
                })

            return json.dumps({
                "main_topics": topics,
                "action_items": action_items,
                "key_decisions": [
                    "Ưu tiên giải quyết triệt để các task BLOCKED trước khi nhận thêm task mới.",
                    "Triển khai kiểm thử tự động trên toàn bộ các endpoint nghiệp vụ."
                ]
            }, ensure_ascii=False)

        # Assignment Recommendation (Feature C)
        if feature is AIFeature.ASSIGNMENT:
            return json.dumps({
                "recommended_user_id": 1,
                "recommended_name": "Phạm Minh Tú",
                "rationale": "Thành viên có năng lực phù hợp nhất với mô tả công việc và đang có khối lượng công việc trong ngưỡng an toàn.",
                "risk_assessment": "Khối lượng công việc khả thi; không có nguy cơ trễ hạn sprint."
            }, ensure_ascii=False)

        # Default: Weekly Summary (Feature A)
        return (
            "### Báo Cáo Tiến Độ Tuần & Nhận Diện Rủi Ro\n\n"
            "**1. Tổng quan tiến độ:**\n"
            "- Các nhiệm vụ phát triển cốt lõi đang được triển khai đúng kế hoạch.\n"
            "- Đã có các đầu việc hoàn thành và chuyển giao vào nhánh kiểm thử.\n\n"
            "**2. Nhận diện rủi ro & Điểm nghẽn (Blockers):**\n"
            "- Cần rà soát các nhiệm vụ đang ở trạng thái BLOCKED để hỗ trợ gỡ vướng kịp thời.\n"
            "- Lưu ý các nhiệm vụ có độ phức tạp cao (XL/L) để tránh dồn ứ cuối sprint.\n\n"
            "**3. Việc cần ưu tiên:**\n"
            "- Tập trung giải phóng các task trên Critical Path.\n"
            "- Thực hiện merge code và chạy test suite tự động trước khi đóng sprint."
        )

    @classmethod
    async def generate_weekly_summary(cls, task_data: List[Dict[str, Any]]) -> str:
        """Feature A: Weekly project progress summary."""
        system_prompt = (
            "Bạn là trợ lý quản lý dự án kỹ thuật. Nhiệm vụ: Tóm tắt tiến độ tuần, "
            "nhận diện rủi ro từ các task bị BLOCKED hoặc quá hạn, và đề xuất việc ưu tiên."
        )
        user_prompt = f"Dữ liệu nhiệm vụ tuần này:\n{json.dumps(task_data, ensure_ascii=False, indent=2)}"
        text, _tier = await cls._call_llm(AIFeature.WEEKLY_SUMMARY, system_prompt, user_prompt)
        return text

    @classmethod
    async def extract_meeting_minutes(cls, raw_notes: str) -> Dict[str, Any]:
        """Feature B: Meeting minutes & action items extractor."""
        system_prompt = (
            "Bạn là trợ lý thư ký dự án. Nhiệm vụ: Trích xuất nội dung cuộc họp thành JSON gồm:\n"
            "1. main_topics (danh sách tóm tắt nội dung)\n"
            "2. action_items (danh sách các object: {title, assignee_name, priority, deadline})\n"
            "3. key_decisions (các quyết định đã chốt).\n"
            "Chỉ trả về định dạng JSON hợp lệ."
        )
        user_prompt = f"Nội dung ghi chép cuộc họp thô:\n{raw_notes}"
        raw_res, _tier = await cls._call_llm(AIFeature.MEETING_MINUTES, system_prompt, user_prompt)
        
        # Clean JSON markdown fences if present
        clean_json = raw_res.strip()
        if clean_json.startswith("```"):
            clean_json = re.sub(r"^```[a-zA-Z]*\n", "", clean_json)
            clean_json = re.sub(r"\n```$", "", clean_json)
        
        try:
            return json.loads(clean_json)
        except Exception:
            # A model answered but not in JSON. That is still a degradation —
            # the user gets canned minutes — so it is logged like one.
            logger.warning(
                "AI tier %s returned unparseable JSON for meeting minutes; "
                "serving the deterministic fallback.", _tier.value,
            )
            return json.loads(cls._deterministic_fallback(AIFeature.MEETING_MINUTES, user_prompt))

    @classmethod
    async def recommend_task_assignment(
        cls, task_title: str, task_desc: str, team_workload: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Feature C: Skill & workload-based assignment recommendation."""
        system_prompt = (
            "Bạn là điều phối viên kỹ thuật. Dựa trên kỹ năng và khối lượng công việc hiện tại "
            "của từng thành viên (số task đang làm, điểm complexity), hãy gợi ý người phù hợp nhất để gán task mới.\n"
            "Trả về JSON: {recommended_user_id, recommended_name, rationale, risk_assessment}"
        )
        user_prompt = (
            f"Nhiệm vụ mới:\nTitle: {task_title}\nDesc: {task_desc}\n\n"
            f"Danh sách thành viên và khối lượng hiện tại:\n{json.dumps(team_workload, ensure_ascii=False, indent=2)}"
        )
        raw_res, _tier = await cls._call_llm(AIFeature.ASSIGNMENT, system_prompt, user_prompt)

        clean_json = raw_res.strip()
        if clean_json.startswith("```"):
            clean_json = re.sub(r"^```[a-zA-Z]*\n", "", clean_json)
            clean_json = re.sub(r"\n```$", "", clean_json)

        try:
            return json.loads(clean_json)
        except Exception:
            logger.warning(
                "AI tier %s returned unparseable JSON for assignment; "
                "serving the deterministic fallback.", _tier.value,
            )
            return json.loads(cls._deterministic_fallback(AIFeature.ASSIGNMENT, user_prompt))
