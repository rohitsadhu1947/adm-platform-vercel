"""
Communication routes — expose WhatsApp templates and call scripts.
"""

from fastapi import APIRouter, HTTPException

from domain.whatsapp_templates import TEMPLATES, TemplateDefinition

router = APIRouter(prefix="/communication", tags=["Communication"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_template(t: TemplateDefinition) -> dict:
    """Serialize a TemplateDefinition to a JSON-safe dict."""
    return {
        "name": t.name,
        "category": t.category,
        "description": t.description,
        "variants": dict(t.variants),
        "buttons": list(t.buttons),
    }


# ---------------------------------------------------------------------------
# Call script definitions
# ---------------------------------------------------------------------------

CALL_SCRIPTS = [
    {
        "name": "First Contact Script",
        "scenario": "first_contact",
        "language": "en",
        "sections": [
            {
                "title": "Opening",
                "content": (
                    "Good morning/afternoon, am I speaking with [Agent Name]? "
                    "My name is [ADM Name] and I am your Agency Development Manager "
                    "from Axis Max Life Insurance. I am calling to welcome you to "
                    "our team and to understand how I can support you in building "
                    "a successful insurance career."
                ),
            },
            {
                "title": "Key Talking Points",
                "bullets": [
                    "Congratulate them on joining and explain the ADM support structure.",
                    "Ask about their background -- previous sales experience, current occupation, and goals.",
                    "Briefly introduce Axis Max Life's product portfolio: Term Life, Endowment, ULIP, and Health plans.",
                    "Explain the first 90-day onboarding journey: training, IRDAI licensing, first sale milestones.",
                    "Confirm their preferred communication channel (WhatsApp, call, in-person) and language (Hindi/English).",
                    "Set expectations: weekly check-ins, training modules via WhatsApp, and joint field visits.",
                ],
            },
            {
                "title": "Common Objections",
                "items": [
                    {
                        "objection": "I am busy with my other job right now.",
                        "response": (
                            "I completely understand. Many of our top-performing agents "
                            "started part-time. Even 30 minutes a day on training can set "
                            "you up for your first sale. Can we schedule a 15-minute call "
                            "at a time that works better for you?"
                        ),
                    },
                    {
                        "objection": "I do not know enough about insurance products yet.",
                        "response": (
                            "That is exactly what I am here for. We have short 2-minute "
                            "training videos on WhatsApp that cover each product. You do not "
                            "need any prior knowledge -- our training is designed for beginners."
                        ),
                    },
                    {
                        "objection": "My friend told me the commission is low.",
                        "response": (
                            "I appreciate you raising that. Our commission structure is "
                            "competitive and IRDAI-regulated. First-year commissions range "
                            "from 15-35 percent depending on the product. Plus, renewal income "
                            "builds every year. Let me share exact numbers with you."
                        ),
                    },
                ],
            },
            {
                "title": "Closing",
                "content": (
                    "Thank you for your time, [Agent Name]. I will send you a "
                    "welcome message on WhatsApp with your first training module. "
                    "Please feel free to reach out to me anytime -- I am here to "
                    "help you succeed. Let us connect again on [day] at [time]. "
                    "Wish you all the best!"
                ),
            },
        ],
    },
    {
        "name": "Dormant Re-engagement Script",
        "scenario": "dormant_reengagement",
        "language": "en",
        "sections": [
            {
                "title": "Opening",
                "content": (
                    "Hello [Agent Name], this is [ADM Name] from Axis Max Life. "
                    "It has been a while since we connected and I wanted to check "
                    "in with you personally. How have you been?"
                ),
            },
            {
                "title": "Empathy Points",
                "bullets": [
                    "Acknowledge the gap without blame: 'I understand things can get busy.'",
                    "Ask open-ended questions: 'What has been keeping you from the insurance work?'",
                    "Listen actively and note the specific reason for dormancy.",
                    "Validate their concerns: 'That is a very common challenge and we have ways to help.'",
                    "Share that many agents face similar situations and come back stronger.",
                ],
            },
            {
                "title": "Incentives",
                "bullets": [
                    "New simplified digital proposal process -- everything can be done on mobile now.",
                    "Refresher training modules available on WhatsApp (just 2 minutes each).",
                    "Joint field visit offer: 'I can accompany you on your first 2-3 customer meetings.'",
                    "Updated commission structures with enhanced first-year payouts on select products.",
                    "Peer success stories: agents who reactivated and achieved targets within 30 days.",
                    "Upcoming product launches that present fresh selling opportunities.",
                ],
            },
            {
                "title": "Closing",
                "content": (
                    "I genuinely want to see you succeed, [Agent Name]. Let us start "
                    "small -- just one training module this week and a short meeting "
                    "to plan your next steps. Can I send you the training link on "
                    "WhatsApp right now? I will also block time for us to meet on "
                    "[day]. Looking forward to working with you again."
                ),
            },
        ],
    },
    {
        "name": "Commission Concern Script",
        "scenario": "commission_concern",
        "language": "en",
        "sections": [
            {
                "title": "Opening",
                "content": (
                    "Hi [Agent Name], this is [ADM Name]. I understand you have "
                    "some questions about the commission structure. I want to walk "
                    "you through everything clearly so there are no doubts. Your "
                    "earning potential is important to us."
                ),
            },
            {
                "title": "Explanation Points",
                "bullets": [
                    "IRDAI regulates commission rates across the industry, ensuring fair and transparent payouts.",
                    "First-year commission rates: Term Life (15-25%), Endowment (25-35%), ULIP (5-8%), Health (15-20%).",
                    "Renewal commissions build a passive income stream -- year 2 onwards, you earn on previously sold policies.",
                    "Persistency bonuses reward agents whose customers continue paying premiums regularly.",
                    "Production-linked incentives: quarterly and annual bonus slabs for consistent performers.",
                    "Top agents at Axis Max Life earn Rs 40,000 to Rs 1,00,000 per month within 12-18 months.",
                ],
            },
            {
                "title": "Comparison Data",
                "bullets": [
                    "Our first-year commission on Term Life is among the highest in the industry.",
                    "Renewal income: an agent with 50 policies earns recurring commission every year without new sales.",
                    "Example: selling 4 policies per month at average Rs 15,000 premium yields approximately Rs 15,000-20,000 monthly income.",
                    "Unlike other companies, we provide digital tools, training, and ADM support at no cost to the agent.",
                    "Axis Max Life's claim settlement ratio is over 99%, which makes selling easier and builds trust.",
                ],
            },
            {
                "title": "Closing",
                "content": (
                    "I hope that gives you a clearer picture, [Agent Name]. "
                    "The key is consistency -- even 2-3 policies a month can "
                    "build meaningful income over time. I am sending you a "
                    "one-page earning calculator on WhatsApp. Let us plan your "
                    "first sale together this week. When is a good time for us to meet?"
                ),
            },
        ],
    },
    {
        "name": "Training Invitation Script",
        "scenario": "training_invitation",
        "language": "en",
        "sections": [
            {
                "title": "Opening",
                "content": (
                    "Hello [Agent Name], this is [ADM Name] from Axis Max Life. "
                    "I am reaching out because we have some excellent training "
                    "resources that I think will really help you. Many agents have "
                    "told me these made a big difference in their confidence and sales."
                ),
            },
            {
                "title": "Benefits",
                "bullets": [
                    "Short, focused modules: each is just 2-3 minutes long and available on WhatsApp.",
                    "Covers everything: product knowledge (Term, ULIP, Health), sales techniques, objection handling.",
                    "Interactive quizzes after each module to reinforce your learning.",
                    "Counts towards your IRDAI continuing education hours for license renewal.",
                    "Top scorers get recognition and priority for joint field visits with the ADM.",
                    "Learn at your own pace -- modules are available 24/7 on your phone.",
                    "Real-world case studies from successful Axis Max Life agents in your region.",
                ],
            },
            {
                "title": "Scheduling",
                "bullets": [
                    "I will send you the first module right after this call on WhatsApp.",
                    "The recommended pace is one module every 2 days -- takes less than 5 minutes.",
                    "After completing 3 modules, we will schedule a 20-minute review call to discuss what you learned.",
                    "Group training sessions are held every Saturday at 10 AM via video call -- would you like to join?",
                    "If you prefer in-person training, I visit [location] every [day] and we can meet then.",
                ],
            },
            {
                "title": "Closing",
                "content": (
                    "Knowledge is the foundation of success in insurance, [Agent Name]. "
                    "The more you know about our products, the more confident you will "
                    "feel when speaking with customers. Let me send you the first module "
                    "now -- just watch it when you have a free moment today. I will "
                    "follow up tomorrow to see how it went. Sound good?"
                ),
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/templates")
def list_templates():
    """Return all registered WhatsApp message templates."""
    return [_serialize_template(t) for t in TEMPLATES.values()]


@router.get("/templates/{name}")
def get_template(name: str):
    """Return a single template by name."""
    template = TEMPLATES.get(name)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{name}' not found")
    return _serialize_template(template)


@router.get("/call-scripts")
def list_call_scripts():
    """Return all call scripts for ADM use.

    Covers four scenarios: first contact, dormant re-engagement,
    commission concerns, and training invitations.
    """
    return CALL_SCRIPTS
