"""
Feedback Intelligence Service — AI-powered classification, routing, and script generation.

Classifies ADM-submitted agent feedback into 5 departmental buckets,
routes tickets with SLAs, and generates communication scripts.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SLA matrix (hours) by bucket x priority
# ---------------------------------------------------------------------------
SLA_MATRIX = {
    "underwriting": {"critical": 12, "high": 24, "medium": 48, "low": 72},
    "finance":      {"critical": 12, "high": 24, "medium": 48, "low": 72},
    "contest":      {"critical": 24, "high": 48, "medium": 72, "low": 120},
    "operations":   {"critical": 4,  "high": 24, "medium": 48, "low": 72},
    "product":      {"critical": 24, "high": 48, "medium": 72, "low": 120},
}

BUCKET_DISPLAY_NAMES = {
    "underwriting": "Underwriting",
    "finance": "Finance",
    "contest": "Contest & Engagement",
    "operations": "Operations",
    "product": "Product",
}


class FeedbackClassifier:
    """Classifies feedback, generates tickets, and creates communication scripts."""

    def __init__(self):
        self.api_key = settings.ANTHROPIC_API_KEY
        self.enabled = settings.ENABLE_AI_FEATURES and bool(self.api_key)

    # ------------------------------------------------------------------
    # Core classification
    # ------------------------------------------------------------------

    async def classify_feedback(
        self,
        raw_text: str,
        selected_reason_codes: Optional[List[str]] = None,
        agent_name: str = "",
        agent_location: str = "",
        agent_state: str = "",
    ) -> dict:
        """
        Classify feedback into bucket + reason code.
        Uses AI if available, falls back to rule-based + selected reasons.

        Returns:
            {
                "bucket": "underwriting",
                "reason_code": "UW-01",
                "secondary_reason_codes": ["UW-06"],
                "confidence": 0.94,
                "priority": "high",
                "urgency_score": 8.0,
                "churn_risk": "high",
                "sentiment": "frustrated",
                "parsed_summary": "Agent reports ...",
                "multi_bucket": false,
                "additional_buckets": []
            }
        """
        # If ADM selected specific reason codes, use them as primary signal
        if selected_reason_codes:
            return self._classify_from_selected_reasons(
                selected_reason_codes, raw_text, agent_name, agent_location
            )

        # AI classification
        if self.enabled and raw_text:
            try:
                return await self._ai_classify(raw_text, agent_name, agent_location, agent_state)
            except Exception as e:
                logger.error(f"AI classification failed: {e}")

        # Fallback: rule-based
        return self._rule_based_classify(raw_text or "")

    def _classify_from_selected_reasons(
        self, codes: List[str], raw_text: str, agent_name: str, agent_location: str
    ) -> dict:
        """Classify based on ADM-selected reason codes."""
        # Determine primary bucket from first selected code
        primary_code = codes[0]
        bucket = self._bucket_from_code(primary_code)

        # Check if multiple buckets are involved
        all_buckets = list({self._bucket_from_code(c) for c in codes})
        multi_bucket = len(all_buckets) > 1

        # Priority: if multiple codes or specific high-priority codes
        priority = "medium"
        if len(codes) >= 3:
            priority = "high"

        summary_parts = []
        if agent_name:
            summary_parts.append(f"Agent {agent_name}")
        if agent_location:
            summary_parts.append(f"({agent_location})")
        summary_parts.append(f"reported issues: {', '.join(codes)}")
        if raw_text:
            summary_parts.append(f"— {raw_text[:200]}")

        return {
            "bucket": bucket,
            "reason_code": primary_code,
            "secondary_reason_codes": codes[1:] if len(codes) > 1 else [],
            "confidence": 1.0,  # ADM explicitly selected
            "priority": priority,
            "urgency_score": 6.0,
            "churn_risk": "medium",
            "sentiment": "neutral",
            "parsed_summary": " ".join(summary_parts),
            "multi_bucket": multi_bucket,
            "additional_buckets": [b for b in all_buckets if b != bucket] if multi_bucket else [],
        }

    async def _ai_classify(
        self, raw_text: str, agent_name: str, agent_location: str, agent_state: str
    ) -> dict:
        """Use Claude AI to classify feedback."""
        import anthropic

        prompt = f"""You are a feedback classification AI for Axis Max Life Insurance.

Classify the following feedback from an ADM (Agency Development Manager) about a dormant/inactive agent.

Agent: {agent_name or 'Unknown'}
Location: {agent_location or 'Unknown'}
Current State: {agent_state or 'Unknown'}

Feedback text: "{raw_text}"

Classify into exactly ONE primary bucket:
- underwriting: Risk selection, policy rejections, pricing, medical requirements, eligibility
- finance: Commissions, payouts, incentive discrepancies, clawback, tax issues
- contest: Contests, recognition, engagement programs, training schedule, marketing material
- operations: Systems, policy issuance, payment gateways, app issues, digital journey
- product: Product complexity, competitiveness, gaps, customer objections on product design

For reason codes, use these prefixes: UW-01 to UW-07, FIN-01 to FIN-08, CON-01 to CON-08, OPS-01 to OPS-08, PRD-01 to PRD-08.

Return ONLY valid JSON:
{{
  "bucket": "underwriting",
  "reason_code": "UW-01",
  "secondary_reason_codes": [],
  "confidence": 0.94,
  "priority": "high",
  "urgency_score": 8.0,
  "churn_risk": "high",
  "sentiment": "frustrated",
  "parsed_summary": "One-line summary of the core issue",
  "multi_bucket": false,
  "additional_buckets": []
}}

Priority rules:
- critical: System outage, multiple agents affected, revenue impact > 5L
- high: Agent mentions joining competitor, recurring issue (3+ similar), frustrated
- medium: Single agent issue, moderate concern
- low: Informational, one-off, agent still engaged"""

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        message = await client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text.strip()

        # Parse JSON
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(response_text)

    def _rule_based_classify(self, raw_text: str) -> dict:
        """Rule-based fallback classifier using keyword matching."""
        text_lower = raw_text.lower()

        # Score each bucket
        bucket_scores = {
            "underwriting": 0, "finance": 0, "contest": 0,
            "operations": 0, "product": 0,
        }
        reason_matches = {}

        uw_keywords = {
            "UW-01": ["rejection", "rejected", "proposal rejected", "declined"],
            "UW-02": ["premium high", "expensive", "costly", "price", "afford"],
            "UW-03": ["medical", "test", "health check", "pre-existing"],
            "UW-05": ["stuck", "pending", "waiting", "processing", "queue"],
        }
        fin_keywords = {
            "FIN-01": ["commission delay", "not paid", "payout delay", "payment pending"],
            "FIN-02": ["commission less", "commission wrong", "calculation"],
            "FIN-03": ["commission stuck", "blocked", "held", "frozen"],
            "FIN-04": ["clawback", "persistency", "reversed", "recovery"],
        }
        con_keywords = {
            "CON-01": ["no contest", "no program", "no motivation"],
            "CON-05": ["no contact", "disconnected", "no support", "nobody calls"],
        }
        ops_keywords = {
            "OPS-01": ["policy issuance", "policy not issued", "generation failed"],
            "OPS-02": ["payment fail", "PG failure", "gateway", "UPI"],
            "OPS-03": ["app", "system", "login", "crash", "not working", "portal"],
        }
        prd_keywords = {
            "PRD-01": ["complex", "complicated", "hard to explain", "confusing"],
            "PRD-02": ["competitor", "LIC", "HDFC", "SBI", "better", "cheaper"],
            "PRD-03": ["low ticket", "small premium", "affordable", "minimum premium"],
        }

        all_keywords = {
            "underwriting": uw_keywords, "finance": fin_keywords,
            "contest": con_keywords, "operations": ops_keywords,
            "product": prd_keywords,
        }

        for bucket, code_map in all_keywords.items():
            for code, keywords in code_map.items():
                for kw in keywords:
                    if kw in text_lower:
                        bucket_scores[bucket] += 1
                        reason_matches.setdefault(bucket, [])
                        if code not in reason_matches[bucket]:
                            reason_matches[bucket].append(code)

        # Pick top bucket
        top_bucket = max(bucket_scores, key=bucket_scores.get)
        if bucket_scores[top_bucket] == 0:
            top_bucket = "operations"  # default if no match

        codes = reason_matches.get(top_bucket, [])
        primary_code = codes[0] if codes else f"{top_bucket[:3].upper()}-01"

        # Sentiment
        neg_words = ["frustrated", "angry", "bad", "worst", "terrible", "leaving", "quit"]
        sentiment = "frustrated" if any(w in text_lower for w in neg_words) else "neutral"

        # Priority
        priority = "medium"
        if any(w in text_lower for w in ["competitor", "lic", "leaving", "quit", "join"]):
            priority = "high"

        return {
            "bucket": top_bucket,
            "reason_code": primary_code,
            "secondary_reason_codes": codes[1:3],
            "confidence": 0.5,
            "priority": priority,
            "urgency_score": 6.0 if priority == "high" else 4.0,
            "churn_risk": "high" if priority == "high" else "medium",
            "sentiment": sentiment,
            "parsed_summary": raw_text[:200] if raw_text else "Feedback submitted via reason selection",
            "multi_bucket": False,
            "additional_buckets": [],
        }

    # ------------------------------------------------------------------
    # Script generation
    # ------------------------------------------------------------------

    async def generate_script(
        self,
        agent_name: str,
        original_feedback: str,
        reason_code: str,
        bucket: str,
        department_response: str,
        agent_location: str = "",
    ) -> str:
        """Generate a communication script for the ADM to use with the agent."""
        if self.enabled:
            try:
                return await self._ai_generate_script(
                    agent_name, original_feedback, reason_code,
                    bucket, department_response, agent_location,
                )
            except Exception as e:
                logger.error(f"AI script generation failed: {e}")

        return self._template_script(
            agent_name, original_feedback, bucket, department_response
        )

    async def _ai_generate_script(
        self,
        agent_name: str,
        original_feedback: str,
        reason_code: str,
        bucket: str,
        department_response: str,
        agent_location: str,
    ) -> str:
        """Use Claude to generate a personalized communication script."""
        import anthropic

        prompt = f"""You are generating a communication script for an ADM (Agency Development Manager)
at Axis Max Life Insurance to use when speaking to a dormant/inactive agent.

Agent Name: {agent_name}
Location: {agent_location}
Original Feedback: "{original_feedback}"
Issue Category: {BUCKET_DISPLAY_NAMES.get(bucket, bucket)}
Reason Code: {reason_code}

Department Response:
"{department_response}"

Generate a communication script in this format:

🗣️ COMMUNICATION SCRIPT
━━━━━━━━━━━━━━━━━━━━━━
📌 Agent: {agent_name}
📌 Issue: [Brief description]

OPENING (Empathetic + Acknowledgment):
[2-3 sentences acknowledging their concern, showing you took action]

CORE MESSAGE (Resolution):
[Key points from the department response, simplified for the agent]

ALTERNATIVE OPTIONS:
[If applicable, alternative approaches or products]

OBJECTION HANDLING:
[2 common objections with suggested responses]

NEXT STEPS:
[2-3 concrete action items with timeline]

CLOSING:
[Encouraging closing statement]
━━━━━━━━━━━━━━━━━━━━━━

Write in a conversational Indian English/Hindi mix style (Hinglish).
Use the agent's name naturally. Be empathetic but professional.
Keep it practical and actionable."""

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        message = await client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()

    def _template_script(
        self, agent_name: str, original_feedback: str, bucket: str, department_response: str
    ) -> str:
        """Template-based fallback script when AI is unavailable."""
        dept_name = BUCKET_DISPLAY_NAMES.get(bucket, bucket)
        return f"""🗣️ COMMUNICATION SCRIPT
━━━━━━━━━━━━━━━━━━━━━━
📌 Agent: {agent_name}
📌 Issue: {dept_name} concern

OPENING:
"{agent_name} ji, I followed up on the concern you raised. I want you to know I took this up directly with our {dept_name} team, and here's what they said."

CORE MESSAGE:
{department_response}

NEXT STEPS:
1. Schedule a follow-up meeting to discuss this in detail
2. If you have any questions, I'm here to help
3. Let's work together to get you back on track

CLOSING:
"{agent_name} ji, your experience matters to us. Let's get this sorted."
━━━━━━━━━━━━━━━━━━━━━━"""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _bucket_from_code(code: str) -> str:
        """Determine bucket from reason code prefix."""
        prefix = code.split("-")[0].upper()
        mapping = {
            "UW": "underwriting",
            "FIN": "finance",
            "CON": "contest",
            "OPS": "operations",
            "PRD": "product",
        }
        return mapping.get(prefix, "operations")

    @staticmethod
    def get_sla_hours(bucket: str, priority: str) -> int:
        """Get SLA hours for a bucket + priority combination."""
        return SLA_MATRIX.get(bucket, {}).get(priority, 48)

    @staticmethod
    def compute_sla_deadline(bucket: str, priority: str) -> datetime:
        """Compute SLA deadline from now."""
        hours = FeedbackClassifier.get_sla_hours(bucket, priority)
        return datetime.utcnow() + timedelta(hours=hours)


# Singleton
feedback_classifier = FeedbackClassifier()
