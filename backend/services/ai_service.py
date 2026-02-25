"""
AI Service using Anthropic Claude API.
Handles product Q&A, feedback analysis, sentiment scoring, and action recommendations.
"""

import json
import logging
from typing import Optional, List
from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Comprehensive Axis Max Life Insurance product knowledge system prompt
# ---------------------------------------------------------------------------
AXIS_MAX_LIFE_SYSTEM_PROMPT = """You are an expert insurance advisor AI for Axis Max Life Insurance (a joint venture between Axis Bank and Max Financial Services). You help Agency Development Managers (ADMs) with product knowledge, agent re-engagement strategies, and objection handling.

## COMPANY OVERVIEW
Axis Max Life Insurance is one of India's leading private life insurance companies. It operates through a multi-channel distribution network including agency, bancassurance (through Axis Bank), online, and partnerships.

## COMPLETE PRODUCT PORTFOLIO

### 1. TERM INSURANCE PLANS

**Max Life Smart Secure Plus Plan**
- Pure term life insurance with affordable premiums
- Sum Assured: Rs 25 lakh to Rs 10 crore
- Policy Term: 10 to 40 years
- Premium Payment: Regular, Limited Pay (5, 7, 10, 12, 15 years)
- Key Features: Terminal illness benefit, accidental death benefit rider
- Tax Benefits: Section 80C (premiums), Section 10(10D) (death benefit)
- USP: Among the most affordable term plans in market

**Max Life Online Term Plan Plus**
- Digital-first term plan with competitive pricing
- Available online with minimal documentation
- Coverage up to Rs 10 crore
- Option for whole life cover (up to age 85)
- Critical illness and accidental death riders available

**Max Life Smart Fixed-Return Digital Plan**
- Guaranteed returns with life cover
- Premium Payment Terms: 5 or 10 years
- Guaranteed additions from year 1
- Maturity benefit with guaranteed returns

### 2. SAVINGS & GUARANTEED RETURN PLANS

**Max Life Smart Wealth Plan**
- Guaranteed income + wealth creation
- Premium Payment: 5, 7, 8, 10, or 12 years
- Policy Term: 15 to 25 years
- Guaranteed additions starting Year 1
- Loyalty additions from Year 11
- Partial withdrawal facility after 5 years

**Max Life Guaranteed Smart Income Plan**
- Regular guaranteed income after premium payment term
- Premium Payment: 6, 8, or 10 years
- Income Period: 25, 30, or 40 years
- Guaranteed annual income as percentage of sum assured
- Joint life option available

**Max Life Smart Secure Savings Plan**
- Endowment-style savings with life cover
- Maturity benefit: Sum Assured + Accrued bonuses
- Premium Payment: Regular or Limited Pay
- Loan facility available after 3 years

**Max Life Forever Young Pension Plan**
- Retirement planning with guaranteed vesting benefit
- Premium Payment: Regular or Single Premium
- Annuity options at vesting
- 1/3rd commutation allowed

### 3. UNIT LINKED INSURANCE PLANS (ULIPs)

**Max Life Online Savings Plan**
- Market-linked returns with life cover
- 4 fund options: Conservative, Balanced, Growth, Aggressive
- Zero premium allocation charge
- Free switching: 12 per year
- Partial withdrawal after 5 years
- Premium: Rs 3,000/month minimum

**Max Life Platinum Wealth Plan**
- Premium ULIP for HNI clients
- Minimum Premium: Rs 2.5 lakh/year
- 7 fund options including mid-cap and multi-cap
- Wealth boosters from Year 6
- Premium Holiday after 5 years allowed

**Max Life Fast Track Super Plan**
- ULIP with accelerated wealth creation
- 11 fund options
- Systematic Transfer facility
- Auto-rebalancing option
- Online fund management

### 4. CHILD PLANS

**Max Life Shiksha Plus Super Plan**
- Comprehensive child education + protection plan
- Premium Waiver on parent's death
- Guaranteed payouts at key milestones (age 18, 21, 24)
- Flexible premium payment terms
- Education fund continues even if parent is no more

**Max Life Super Investment Plan**
- Child-focused ULIP with wealth creation
- Multiple fund options
- Partial withdrawal for education milestones
- Premium waiver benefit

### 5. RETIREMENT PLANS

**Max Life Guaranteed Lifetime Income Plan**
- Lifelong guaranteed pension
- Premium Payment: 5, 7, 10, or 12 years
- Deferred annuity option
- Joint life option for spouse continuation
- Income Tax benefits under 80CCC

**Max Life Forever Young Pension Plan**
- Flexible retirement corpus builder
- Multiple payout options at retirement
- Life cover during accumulation phase
- Tax benefits under Section 80CCC

### 6. HEALTH & CRITICAL ILLNESS

**Max Life Critical Illness and Disability Rider**
- Covers 64 critical illnesses
- Lump sum payout on diagnosis
- Available as rider with any base plan
- Waiting period: 90 days (for certain illnesses)

**Max Life Hospital Cash Rider**
- Daily hospital cash benefit
- No bills required - fixed daily payout
- Covers ICU with enhanced benefit
- Available as add-on rider

### 7. GROUP INSURANCE

**Max Life Group Term Life Insurance**
- For employers and associations
- Customizable sum assured per member
- Competitive group pricing
- Easy onboarding and claims process

**Max Life Group Credit Life Insurance**
- Covers outstanding loan on borrower's death
- For banks, NBFCs, and financial institutions
- Reducing or level cover options

**Max Life Group Gratuity Plan**
- Funding vehicle for gratuity liability
- Investment options with professional fund management
- Tax efficient for employers

### 8. RIDERS (ADD-ONS)

- **Accidental Death Benefit Rider**: Additional SA on accidental death
- **Critical Illness Rider**: 64 critical illnesses covered
- **Waiver of Premium Rider**: Premiums waived on disability/CI
- **Hospital Cash Rider**: Daily hospitalization benefit
- **Term Plus Rider**: Additional term cover
- **Accidental Total Permanent Disability Rider**: Lump sum on ATPD

## KEY COMMISSION STRUCTURE (INDICATIVE)
- Term Plans: 15-30% first year, 5-7.5% renewal
- Traditional Savings: 20-35% first year, 5-7.5% renewal
- ULIPs: 5-8% of premium across years
- Group Plans: Varies by scheme size
- Riders: Additional commission on rider premium

## COMPETITIVE ADVANTAGES
1. Axis Bank distribution strength (5,000+ branches)
2. Claims settlement ratio: ~99.51% (among highest in industry)
3. Comprehensive digital tools and paperless processes
4. Strong brand trust (Axis Bank + Max Life)
5. Wide product range covering all life stages
6. Competitive pricing especially in term insurance
7. Robust training and support for agents

## COMMON AGENT OBJECTIONS AND RESPONSES

**"Commission rates are too low"**
- Focus on volume-based incentives and bonus structures
- Highlight digital tools that help close more policies
- Compare total earning potential vs competitors
- Emphasize persistency bonuses for renewals

**"Products are complex to explain"**
- Use Max Life's digital sales tools and benefit illustrations
- Focus on 2-3 core products initially
- Leverage ready-made pitch materials
- Customer-facing app simplifies explanation

**"Market competition is tough"**
- Highlight claims settlement ratio advantage
- Focus on Axis Bank brand trust
- Use comparison tools to show product superiority
- Emphasize customer service quality

**"I don't have enough leads"**
- Explain referral programs and incentives
- Digital lead generation support
- Axis Bank branch referral program
- Social media and digital marketing support

**"System/portal issues"**
- Escalation paths for tech issues
- Alternative manual processes
- Training on digital tools
- Dedicated helpdesk numbers

## ADM ENGAGEMENT STRATEGIES

### For Dormant Agents (180+ days inactive):
1. Personal call - understand root cause
2. Share success stories of reactivated agents
3. Offer refresher training
4. Pair with a buddy (active agent)
5. Set small, achievable first-week targets

### For At-Risk Agents (60-180 days):
1. Proactive check-in before dormancy
2. Address specific concerns immediately
3. Provide targeted product training
4. Help with pending cases/proposals
5. Connect with branch for lead support

### For Newly Contacted Agents:
1. Schedule regular touchpoints
2. Set 30-60-90 day goals
3. Monitor first policy submission closely
4. Provide hands-on support for first sale
5. Celebrate small wins

ALWAYS provide specific, actionable advice. Reference exact product names and features.
When suggesting products for customer scenarios, recommend 2-3 options with brief reasoning.
Keep responses concise but thorough - ADMs are busy professionals.
Use Indian insurance terminology and context.
Currency is always in Indian Rupees (Rs or INR).
"""


class AIService:
    """Service for AI-powered features using Anthropic Claude."""

    def __init__(self):
        self.api_key = settings.ANTHROPIC_API_KEY
        self.enabled = settings.ENABLE_AI_FEATURES and bool(self.api_key)

    async def _call_claude(
        self,
        user_message: str,
        system_prompt: str = AXIS_MAX_LIFE_SYSTEM_PROMPT,
        max_tokens: int = 1024,
    ) -> str:
        """Make a call to the Anthropic Claude API."""
        if not self.enabled:
            return self._fallback_response(user_message)

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return self._fallback_response(user_message)

    def _fallback_response(self, question: str) -> str:
        """Provide a basic fallback when AI is unavailable."""
        question_lower = question.lower()

        if any(w in question_lower for w in ["term", "protection", "smart secure"]):
            return (
                "Max Life Smart Secure Plus Plan is our flagship term insurance offering "
                "coverage from Rs 25 lakh to Rs 10 crore with premium payment options of "
                "regular or limited pay (5, 7, 10, 12, 15 years). Key features include "
                "terminal illness benefit and accidental death benefit rider. "
                "Tax benefits available under Section 80C and 10(10D)."
            )
        if any(w in question_lower for w in ["ulip", "unit linked", "market"]):
            return (
                "Max Life offers several ULIPs: Online Savings Plan (zero allocation charge, "
                "4 fund options), Platinum Wealth Plan (for HNI, min Rs 2.5L/year, 7 funds), "
                "and Fast Track Super Plan (11 fund options with auto-rebalancing). "
                "All ULIPs have a 5-year lock-in as per IRDAI guidelines."
            )
        if any(w in question_lower for w in ["child", "shiksha", "education"]):
            return (
                "Max Life Shiksha Plus Super Plan provides guaranteed payouts at age 18, 21, "
                "and 24 for education milestones. Premium waiver ensures the fund continues "
                "even if the parent passes away. Flexible premium payment terms available."
            )
        if any(w in question_lower for w in ["pension", "retirement", "annuity"]):
            return (
                "For retirement, we offer the Guaranteed Lifetime Income Plan (lifelong pension, "
                "5-12 year premium payment) and Forever Young Pension Plan (flexible corpus builder). "
                "Both offer tax benefits under Section 80CCC."
            )
        if any(w in question_lower for w in ["commission", "earning", "income"]):
            return (
                "Commission structure: Term plans 15-30% first year (5-7.5% renewal), "
                "Traditional savings 20-35% first year (5-7.5% renewal), ULIPs 5-8%. "
                "Additional earnings through persistency bonuses, contest rewards, and "
                "volume-based incentives."
            )
        if any(w in question_lower for w in ["dormant", "inactive", "reactivat"]):
            return (
                "For dormant agent reactivation: 1) Personal call to understand root cause, "
                "2) Share success stories, 3) Offer refresher training, 4) Pair with active "
                "agent buddy, 5) Set small achievable first-week targets. Focus on removing "
                "specific barriers the agent faces."
            )

        return (
            "Axis Max Life Insurance offers a comprehensive product portfolio including "
            "term insurance, savings plans, ULIPs, child plans, retirement plans, and "
            "group insurance. With a claims settlement ratio of ~99.51% and Axis Bank's "
            "distribution network, we provide strong support for agents. "
            "Please ask a more specific question for detailed product information."
        )

    async def answer_product_question(
        self, question: str, context: Optional[str] = None
    ) -> dict:
        """Answer a product-related question."""
        prompt = question
        if context:
            prompt = f"Context: {context}\n\nQuestion: {question}"

        answer = await self._call_claude(prompt)

        # Determine suggested products from the answer
        products = []
        product_keywords = {
            "Smart Secure Plus": "term",
            "Online Term Plan": "term",
            "Smart Wealth": "savings",
            "Guaranteed Smart Income": "savings",
            "Online Savings Plan": "ulip",
            "Platinum Wealth": "ulip",
            "Shiksha Plus": "child",
            "Guaranteed Lifetime Income": "pension",
            "Forever Young Pension": "pension",
        }
        for product_name, _ in product_keywords.items():
            if product_name.lower() in answer.lower():
                products.append(product_name)

        return {
            "answer": answer,
            "confidence": 0.85 if self.enabled else 0.5,
            "suggested_products": products[:5],
            "follow_up_questions": [
                "What are the premium payment options?",
                "How does the commission structure work for this product?",
                "What are the key selling points vs competitors?",
            ],
        }

    async def analyze_feedback(
        self, raw_text: str, agent_context: Optional[str] = None
    ) -> dict:
        """Analyze agent feedback text to extract category, sentiment, priority."""
        prompt = f"""Analyze the following feedback from an insurance agent and return a JSON object with these fields:
- category: one of [system_issues, commission_concerns, market_conditions, product_complexity, personal_reasons, competition, support_issues]
- subcategory: a specific subcategory (e.g., "portal_downtime", "low_first_year_commission", "term_plan_pricing", etc.)
- sentiment: one of [positive, neutral, negative]
- priority: one of [low, medium, high, critical]
- summary: a one-line summary of the feedback
- recommended_actions: list of 2-3 specific actionable steps for the ADM

Agent Feedback: "{raw_text}"
"""
        if agent_context:
            prompt += f"\nAgent Context: {agent_context}"

        prompt += "\n\nRespond ONLY with valid JSON, no markdown formatting."

        response = await self._call_claude(prompt, max_tokens=512)

        try:
            # Try to parse JSON from response
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            result = json.loads(cleaned)
            return result
        except (json.JSONDecodeError, IndexError):
            # Fallback analysis
            return self._rule_based_feedback_analysis(raw_text)

    def _rule_based_feedback_analysis(self, raw_text: str) -> dict:
        """Rule-based fallback for feedback analysis."""
        text_lower = raw_text.lower()

        # Determine category
        category = "support_issues"
        subcategory = "general"

        if any(w in text_lower for w in ["portal", "system", "app", "login", "server", "error", "bug"]):
            category = "system_issues"
            subcategory = "portal_issues"
        elif any(w in text_lower for w in ["commission", "pay", "earning", "income", "money"]):
            category = "commission_concerns"
            subcategory = "commission_rate"
        elif any(w in text_lower for w in ["market", "economy", "demand", "customer"]):
            category = "market_conditions"
            subcategory = "low_demand"
        elif any(w in text_lower for w in ["complex", "confusing", "understand", "product"]):
            category = "product_complexity"
            subcategory = "product_understanding"
        elif any(w in text_lower for w in ["personal", "health", "family", "time"]):
            category = "personal_reasons"
            subcategory = "personal_commitments"
        elif any(w in text_lower for w in ["competitor", "other company", "lic", "hdfc", "sbi"]):
            category = "competition"
            subcategory = "competitor_offering"

        # Determine sentiment
        negative_words = ["bad", "poor", "worst", "terrible", "frustrated", "angry", "disappointed", "issue", "problem"]
        positive_words = ["good", "great", "happy", "satisfied", "excellent", "helpful"]
        neg_count = sum(1 for w in negative_words if w in text_lower)
        pos_count = sum(1 for w in positive_words if w in text_lower)

        if neg_count > pos_count:
            sentiment = "negative"
        elif pos_count > neg_count:
            sentiment = "positive"
        else:
            sentiment = "neutral"

        # Determine priority
        priority = "medium"
        if any(w in text_lower for w in ["urgent", "critical", "immediately", "worst"]):
            priority = "critical"
        elif any(w in text_lower for w in ["frustrated", "angry", "leaving", "quit"]):
            priority = "high"
        elif sentiment == "positive":
            priority = "low"

        return {
            "category": category,
            "subcategory": subcategory,
            "sentiment": sentiment,
            "priority": priority,
            "summary": raw_text[:100] + ("..." if len(raw_text) > 100 else ""),
            "recommended_actions": [
                f"Address {category.replace('_', ' ')} concern with the agent",
                "Schedule a follow-up call within 48 hours",
                "Document the feedback and escalate if needed",
            ],
        }

    async def get_action_recommendations(
        self,
        agent_data: dict,
        interaction_history: list,
        feedback_history: list,
    ) -> dict:
        """Get AI-powered action recommendations for an agent."""
        prompt = f"""Based on the following agent profile and history, recommend specific next actions for the ADM:

Agent Profile:
- Name: {agent_data.get('name', 'N/A')}
- Location: {agent_data.get('location', 'N/A')}
- State: {agent_data.get('lifecycle_state', 'dormant')}
- Dormancy Reason: {agent_data.get('dormancy_reason', 'Unknown')}
- Dormancy Duration: {agent_data.get('dormancy_duration_days', 0)} days
- Engagement Score: {agent_data.get('engagement_score', 0)}/100
- Language: {agent_data.get('language', 'Hindi')}

Recent Interactions ({len(interaction_history)} total):
"""
        for interaction in interaction_history[:5]:
            prompt += f"- {interaction.get('type', 'call')}: {interaction.get('outcome', 'N/A')} - {interaction.get('notes', '')[:80]}\n"

        prompt += f"\nFeedback History ({len(feedback_history)} items):\n"
        for fb in feedback_history[:5]:
            prompt += f"- [{fb.get('category', 'N/A')}] {fb.get('raw_text', '')[:80]}\n"

        prompt += """
Provide a JSON response with:
- recommended_actions: list of 3-5 specific, actionable steps (each with "action", "timeline", "channel")
- priority: one of [low, medium, high, critical]
- reasoning: brief explanation of the recommendation strategy

Respond ONLY with valid JSON."""

        response = await self._call_claude(prompt, max_tokens=768)

        try:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(cleaned)
        except (json.JSONDecodeError, IndexError):
            # Fallback
            state = agent_data.get("lifecycle_state", "dormant")
            if state == "dormant":
                return {
                    "recommended_actions": [
                        {"action": "Make a personal phone call to understand dormancy reason", "timeline": "Today", "channel": "call"},
                        {"action": "Send WhatsApp message with recent success stories", "timeline": "Today", "channel": "whatsapp"},
                        {"action": "Schedule a face-to-face meeting if phone call is successful", "timeline": "This week", "channel": "visit"},
                        {"action": "Offer refresher training on current product portfolio", "timeline": "Within 2 weeks", "channel": "training"},
                    ],
                    "priority": "high",
                    "reasoning": f"Agent has been dormant for {agent_data.get('dormancy_duration_days', 0)} days. Immediate re-engagement needed with personal touch.",
                }
            else:
                return {
                    "recommended_actions": [
                        {"action": "Follow up on previous interaction", "timeline": "Within 48 hours", "channel": "call"},
                        {"action": "Share relevant product updates", "timeline": "This week", "channel": "whatsapp"},
                        {"action": "Set weekly check-in schedule", "timeline": "Ongoing", "channel": "call"},
                    ],
                    "priority": "medium",
                    "reasoning": f"Agent is in {state} state. Consistent engagement needed to move towards activation.",
                }

    async def compute_sentiment_score(self, text: str) -> float:
        """Compute a sentiment score from -1.0 (very negative) to 1.0 (very positive)."""
        if not text:
            return 0.0

        text_lower = text.lower()
        negative_words = [
            "bad", "poor", "worst", "terrible", "frustrated", "angry",
            "disappointed", "issue", "problem", "not working", "failure",
            "quit", "leaving", "unhappy", "waste", "useless",
        ]
        positive_words = [
            "good", "great", "happy", "satisfied", "excellent", "helpful",
            "thanks", "appreciate", "wonderful", "amazing", "interested",
            "motivated", "ready", "excited",
        ]

        neg_count = sum(1 for w in negative_words if w in text_lower)
        pos_count = sum(1 for w in positive_words if w in text_lower)
        total = neg_count + pos_count

        if total == 0:
            return 0.0

        score = (pos_count - neg_count) / total
        return round(max(-1.0, min(1.0, score)), 2)


# Singleton instance
ai_service = AIService()
