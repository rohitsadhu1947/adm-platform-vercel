"""
domain/dormancy_taxonomy.py — Full dormancy reason taxonomy.

Ported from AARS seeds/dormancy_taxonomy.py. Contains all 27 dormancy
reason codes mapped to 7 categories with detection hints, suggested actions,
and bilingual labels (Hindi + English).

This taxonomy powers:
- Dormancy reason classification from voice/chat conversations
- ADM nudge messages explaining WHY an agent is dormant
- Playbook selection (which reactivation approach to use)
- Dashboard analytics (dormancy breakdown charts)
"""
from __future__ import annotations

from domain.enums import DormancyReasonCategory, DormancyReasonCode


# ---------------------------------------------------------------------------
# Full Taxonomy — 27 reasons across 7 categories
# ---------------------------------------------------------------------------

DORMANCY_TAXONOMY: list[dict] = [
    # ===== TRAINING GAP (5 reasons) ========================================
    {
        "code": DormancyReasonCode.PRODUCT_KNOWLEDGE_INSUFFICIENT,
        "category": DormancyReasonCategory.TRAINING_GAP,
        "name_en": "Product Knowledge Insufficient",
        "name_hi": "Product ki jaankari kam hai",
        "description_en": "Agent lacks knowledge about insurance products and cannot explain them to customers.",
        "description_hi": "Agent ko insurance products ki samajh nahi hai aur woh customers ko explain nahi kar pata.",
        "detection_hints": [
            "product", "understand", "confused", "don't know", "what is",
            "term life", "endowment", "ulip", "explain", "features",
            "samajh", "pata nahi", "kya hai",
        ],
        "suggested_playbook": "training_gap_product_knowledge",
        "suggested_action_en": "Send product training modules and schedule a guided learning session",
        "suggested_action_hi": "Product training bhejein aur guided learning session schedule karein",
        "adm_talking_points": [
            "Ask which product they find most confusing",
            "Offer to do a joint customer visit to demonstrate",
            "Share simple one-pager product comparison",
        ],
    },
    {
        "code": DormancyReasonCode.SALES_SKILLS_LACKING,
        "category": DormancyReasonCategory.TRAINING_GAP,
        "name_en": "Sales Skills Lacking",
        "name_hi": "Selling skills ki kami",
        "description_en": "Agent struggles with selling techniques — prospecting, pitching, objection handling, closing.",
        "description_hi": "Agent ko selling techniques mein dikkat hai — customer dhundhna, pitch karna, objections handle karna.",
        "detection_hints": [
            "sell", "pitch", "customer", "objection", "convince",
            "approach", "closing", "prospect", "rejection",
            "bechna", "customer nahi milta", "mana kar deta",
        ],
        "suggested_playbook": "training_gap_sales_skills",
        "suggested_action_en": "Assign sales skill training and pair with a successful agent for mentoring",
        "suggested_action_hi": "Sales training assign karein aur ek successful agent ke saath pair karein",
        "adm_talking_points": [
            "Ask about their last 3 customer interactions",
            "Role-play a sales conversation together",
            "Share success stories from other agents in the region",
        ],
    },
    {
        "code": DormancyReasonCode.EXAM_NOT_ATTEMPTED,
        "category": DormancyReasonCategory.TRAINING_GAP,
        "name_en": "Exam Not Attempted",
        "name_hi": "Exam nahi diya",
        "description_en": "Agent has not attempted the IRDAI/IC38 licensing exam yet.",
        "description_hi": "Agent ne abhi tak IRDAI/IC38 licensing exam nahi diya hai.",
        "detection_hints": [
            "exam", "IC38", "IRDAI", "test", "license exam", "not attempted",
            "pariksha", "nahi diya",
        ],
        "suggested_playbook": "training_gap_exam_prep",
        "suggested_action_en": "Help schedule exam and provide preparation material",
        "suggested_action_hi": "Exam schedule karne mein madad karein aur preparation material dein",
        "adm_talking_points": [
            "Find out what is blocking them from scheduling the exam",
            "Offer to help with the registration process",
            "Share exam tips and mock tests",
        ],
    },
    {
        "code": DormancyReasonCode.EXAM_FAILED,
        "category": DormancyReasonCategory.TRAINING_GAP,
        "name_en": "Exam Failed",
        "name_hi": "Exam mein fail",
        "description_en": "Agent failed the licensing exam and needs to prepare for retake.",
        "description_hi": "Agent licensing exam mein fail ho gaya hai aur dobara dena hai.",
        "detection_hints": [
            "failed", "exam", "IC38", "not passed", "retake",
            "fail", "dobara", "pass nahi hua",
        ],
        "suggested_playbook": "training_gap_exam_prep",
        "suggested_action_en": "Provide focused preparation material for weak areas and schedule retake",
        "suggested_action_hi": "Kamzor areas ke liye focused material dein aur retake schedule karein",
        "adm_talking_points": [
            "Encourage them — many successful agents failed the first time",
            "Identify specific topics they found difficult",
            "Set up a study schedule with daily targets",
        ],
    },
    {
        "code": DormancyReasonCode.PROCESS_UNCLEAR,
        "category": DormancyReasonCategory.TRAINING_GAP,
        "name_en": "Process Unclear",
        "name_hi": "Process samajh nahi aata",
        "description_en": "Agent doesn't understand operational processes (proposal, KYC, issuance).",
        "description_hi": "Agent ko operational processes samajh nahi aate (proposal, KYC, policy issuance).",
        "detection_hints": [
            "process", "form", "proposal", "KYC", "how to", "steps",
            "document", "submit", "procedure",
            "kaise karna hai", "form bharein", "kya karna hai",
        ],
        "suggested_playbook": "training_gap_process",
        "suggested_action_en": "Send process training and offer hands-on help with first proposal",
        "suggested_action_hi": "Process training bhejein aur pehle proposal mein haath pakad ke madad karein",
        "adm_talking_points": [
            "Walk them through a complete proposal step by step",
            "Share a checklist of documents needed",
            "Do a screen-share session for digital tools",
        ],
    },

    # ===== ENGAGEMENT GAP (4 reasons) ======================================
    {
        "code": DormancyReasonCode.ADM_NEVER_CONTACTED,
        "category": DormancyReasonCategory.ENGAGEMENT_GAP,
        "name_en": "ADM Never Contacted",
        "name_hi": "ADM ne kabhi contact nahi kiya",
        "description_en": "Agent was onboarded but their ADM has never reached out to them.",
        "description_hi": "Agent ka onboarding ho gaya lekin ADM ne kabhi contact nahi kiya.",
        "detection_hints": [
            "no one called", "nobody contacted", "manager", "ADM",
            "never met", "no support", "alone",
            "kisi ne call nahi kiya", "koi nahi aaya", "akela",
        ],
        "suggested_playbook": "engagement_gap_adm_never_contacted",
        "suggested_action_en": "ADM to make immediate first contact call and schedule an in-person meeting",
        "suggested_action_hi": "ADM turant pehla call karein aur milne ka plan banayein",
        "adm_talking_points": [
            "Apologize for the delay in reaching out",
            "Ask about their background and goals",
            "Set up a regular weekly check-in schedule",
        ],
    },
    {
        "code": DormancyReasonCode.ADM_NO_FOLLOWTHROUGH,
        "category": DormancyReasonCategory.ENGAGEMENT_GAP,
        "name_en": "ADM No Follow-Through",
        "name_hi": "ADM ne follow-up nahi kiya",
        "description_en": "ADM made initial contact but never followed up on commitments.",
        "description_hi": "ADM ne pehla contact kiya lekin baad mein follow-up nahi kiya.",
        "detection_hints": [
            "promised", "follow up", "didn't call back", "no follow",
            "waiting", "said would help",
            "bola tha", "call nahi kiya", "intezaar",
        ],
        "suggested_playbook": "engagement_gap_followthrough",
        "suggested_action_en": "ADM to acknowledge gap and re-establish regular contact pattern",
        "suggested_action_hi": "ADM accept karein ki gap ho gaya aur regular contact pattern banayein",
        "adm_talking_points": [
            "Acknowledge the delay honestly",
            "Ask what specific help they need right now",
            "Set a recurring calendar reminder for follow-ups",
        ],
    },
    {
        "code": DormancyReasonCode.FEELS_UNSUPPORTED,
        "category": DormancyReasonCategory.ENGAGEMENT_GAP,
        "name_en": "Feels Unsupported",
        "name_hi": "Support nahi milta",
        "description_en": "Agent feels they don't have adequate support from the company or ADM.",
        "description_hi": "Agent ko lagta hai ki company ya ADM se koi support nahi milta.",
        "detection_hints": [
            "support", "help", "alone", "nobody", "unsupported",
            "on my own", "no guidance",
            "madad nahi", "akela", "koi nahi hai",
        ],
        "suggested_playbook": "engagement_gap_support",
        "suggested_action_en": "Increase touchpoints and create a personalized support plan",
        "suggested_action_hi": "Zyada touchpoints rakhein aur personalized support plan banayein",
        "adm_talking_points": [
            "Listen empathetically to their specific frustrations",
            "Create a concrete 30-day support plan together",
            "Introduce them to a peer group of agents in the area",
        ],
    },
    {
        "code": DormancyReasonCode.NO_RECOGNITION,
        "category": DormancyReasonCategory.ENGAGEMENT_GAP,
        "name_en": "No Recognition",
        "name_hi": "Recognition nahi mila",
        "description_en": "Agent feels their efforts and achievements are not recognized.",
        "description_hi": "Agent ko lagta hai ki unki mehnat aur achievements ko recognize nahi kiya jaata.",
        "detection_hints": [
            "recognition", "appreciate", "ignored", "no reward",
            "not valued", "incentive",
            "koi appreciate nahi karta", "value nahi", "reward nahi",
        ],
        "suggested_playbook": "engagement_gap_recognition",
        "suggested_action_en": "Celebrate recent achievements and set up a recognition program",
        "suggested_action_hi": "Recent achievements celebrate karein aur recognition program shuru karein",
        "adm_talking_points": [
            "Specifically mention their recent positive contributions",
            "Discuss upcoming contests and recognition opportunities",
            "Share how top agents are recognized and rewarded",
        ],
    },

    # ===== ECONOMIC (4 reasons) ============================================
    {
        "code": DormancyReasonCode.COMMISSION_TOO_LOW,
        "category": DormancyReasonCategory.ECONOMIC,
        "name_en": "Commission Too Low",
        "name_hi": "Commission kam hai",
        "description_en": "Agent perceives commission rates as too low to be worthwhile.",
        "description_hi": "Agent ko lagta hai ki commission rates bahut kam hain.",
        "detection_hints": [
            "commission", "earning", "money", "income", "low pay",
            "not enough", "payout", "not worth",
            "paise kam", "kamai nahi", "commission nahi milta",
        ],
        "suggested_playbook": "economic_commission_concerns",
        "suggested_action_en": "Explain commission structure, show earning scenarios, discuss product mix",
        "suggested_action_hi": "Commission structure samjhayein, earning scenarios dikhayein, product mix discuss karein",
        "adm_talking_points": [
            "Show concrete earning examples from successful agents",
            "Explain the full commission structure including renewals",
            "Suggest higher-commission product categories",
        ],
    },
    {
        "code": DormancyReasonCode.COMPETITOR_BETTER_COMMISSION,
        "category": DormancyReasonCategory.ECONOMIC,
        "name_en": "Competitor Better Commission",
        "name_hi": "Doosri company zyada commission deti hai",
        "description_en": "Agent knows of competitors offering better commission rates.",
        "description_hi": "Agent ko pata hai ki doosri companies zyada commission deti hain.",
        "detection_hints": [
            "other company", "competitor", "better rate", "LIC",
            "HDFC", "ICICI", "more commission",
            "doosri company", "zyada milta hai", "competitor",
        ],
        "suggested_playbook": "economic_commission_concerns",
        "suggested_action_en": "Discuss total value proposition (support, training, tools) beyond just rates",
        "suggested_action_hi": "Sirf rates nahi, total value proposition discuss karein (support, training, tools)",
        "adm_talking_points": [
            "Acknowledge the concern without being defensive",
            "Highlight non-commission benefits (training, digital tools, support)",
            "Show long-term earning potential with renewals and persistency bonuses",
        ],
    },
    {
        "code": DormancyReasonCode.IRREGULAR_PAYMENTS,
        "category": DormancyReasonCategory.ECONOMIC,
        "name_en": "Irregular Payments",
        "name_hi": "Payment samay pe nahi aata",
        "description_en": "Agent experiences delays or irregularity in commission payments.",
        "description_hi": "Agent ko commission payments mein delay ya irregularity hoti hai.",
        "detection_hints": [
            "payment", "delayed", "not received", "pending",
            "irregular", "late payment",
            "payment nahi aaya", "pending hai", "late ho gaya",
        ],
        "suggested_playbook": "economic_payment_issue",
        "suggested_action_en": "Investigate specific pending payments and resolve; set expectations for future",
        "suggested_action_hi": "Specific pending payments check karein aur resolve karein",
        "adm_talking_points": [
            "Get specific details: which policies, how much, when expected",
            "Escalate to operations team with concrete cases",
            "Follow up within 48 hours with a resolution update",
        ],
    },
    {
        "code": DormancyReasonCode.INSUFFICIENT_INCOME,
        "category": DormancyReasonCategory.ECONOMIC,
        "name_en": "Insufficient Income",
        "name_hi": "Income kaafi nahi hai",
        "description_en": "Agent cannot sustain themselves on insurance commission alone.",
        "description_hi": "Agent sirf insurance commission se apna guzara nahi kar sakta.",
        "detection_hints": [
            "full-time", "part-time", "other job", "not enough",
            "sustain", "livelihood", "income",
            "poora time nahi de sakta", "doosra kaam", "guzara nahi hota",
        ],
        "suggested_playbook": "economic_income_support",
        "suggested_action_en": "Help create a realistic income plan; suggest part-time selling strategies",
        "suggested_action_hi": "Realistic income plan banayein; part-time selling strategies suggest karein",
        "adm_talking_points": [
            "Understand their financial situation empathetically",
            "Create a realistic monthly target and plan",
            "Suggest warm-market strategies that work part-time",
        ],
    },

    # ===== OPERATIONAL (5 reasons) =========================================
    {
        "code": DormancyReasonCode.PROPOSAL_PROCESS_COMPLEX,
        "category": DormancyReasonCategory.OPERATIONAL,
        "name_en": "Proposal Process Complex",
        "name_hi": "Proposal process bahut complicated hai",
        "description_en": "Agent finds the proposal/application process too complicated.",
        "description_hi": "Agent ko proposal/application process bahut complicated lagta hai.",
        "detection_hints": [
            "proposal", "form", "complicated", "difficult", "complex",
            "too many", "paperwork",
            "form bahut mushkil", "complicated hai", "samajh nahi aata",
        ],
        "suggested_playbook": "operational_process_simplification",
        "suggested_action_en": "Provide step-by-step process guide and hands-on help with next proposal",
        "suggested_action_hi": "Step-by-step guide dein aur agle proposal mein haath pakad ke madad karein",
        "adm_talking_points": [
            "Ask which specific part of the process confuses them",
            "Walk through a complete proposal together on a call",
            "Share digital tools that simplify the process",
        ],
    },
    {
        "code": DormancyReasonCode.TECHNOLOGY_BARRIERS,
        "category": DormancyReasonCategory.OPERATIONAL,
        "name_en": "Technology Barriers",
        "name_hi": "Technology mein dikkat",
        "description_en": "Agent struggles with digital tools and apps required for business.",
        "description_hi": "Agent ko digital tools aur apps use karne mein dikkat hoti hai.",
        "detection_hints": [
            "app", "technology", "digital", "phone", "internet",
            "computer", "login", "technical",
            "app nahi chalta", "samajh nahi aata", "technical dikkat",
        ],
        "suggested_playbook": "operational_tech_support",
        "suggested_action_en": "Schedule a digital literacy session and provide step-by-step app guides",
        "suggested_action_hi": "Digital literacy session schedule karein aur app guides dein",
        "adm_talking_points": [
            "Find out which specific tools they struggle with",
            "Offer a screen-share walkthrough session",
            "Pair them with a tech-savvy agent for peer support",
        ],
    },
    {
        "code": DormancyReasonCode.CLAIM_EXPERIENCE_BAD,
        "category": DormancyReasonCategory.OPERATIONAL,
        "name_en": "Bad Claim Experience",
        "name_hi": "Claim ka bura experience",
        "description_en": "Agent or their customers had bad claims experience, damaging trust.",
        "description_hi": "Agent ya unke customers ka claim experience kharab raha, bharosa toot gaya.",
        "detection_hints": [
            "claim", "rejected", "denied", "customer angry",
            "bad experience", "trust",
            "claim reject", "customer gussa", "bharosa nahi",
        ],
        "suggested_playbook": "operational_claim_support",
        "suggested_action_en": "Investigate the specific claim case and help resolve; rebuild confidence",
        "suggested_action_hi": "Specific claim case investigate karein aur resolve karein; confidence rebuild karein",
        "adm_talking_points": [
            "Get details of the specific claim that went wrong",
            "Escalate to claims team and follow up personally",
            "Share claim settlement ratio data to rebuild confidence",
        ],
    },
    {
        "code": DormancyReasonCode.SLOW_ISSUANCE,
        "category": DormancyReasonCategory.OPERATIONAL,
        "name_en": "Slow Policy Issuance",
        "name_hi": "Policy issue hone mein bahut der lagti hai",
        "description_en": "Policies take too long to issue, frustrating agents and customers.",
        "description_hi": "Policies issue hone mein bahut time lagta hai, agents aur customers frustrated hain.",
        "detection_hints": [
            "issuance", "slow", "delay", "policy not issued",
            "pending", "waiting for policy",
            "policy nahi aayi", "delay ho raha", "intezaar",
        ],
        "suggested_playbook": "operational_issuance_support",
        "suggested_action_en": "Check pending policies, escalate stuck cases, set realistic timelines",
        "suggested_action_hi": "Pending policies check karein, stuck cases escalate karein, timeline batayein",
        "adm_talking_points": [
            "Get specific policy numbers and check status",
            "Escalate to operations with urgency",
            "Update the agent within 24 hours on resolution",
        ],
    },
    {
        "code": DormancyReasonCode.KYC_ISSUES,
        "category": DormancyReasonCategory.OPERATIONAL,
        "name_en": "KYC Issues",
        "name_hi": "KYC mein problem",
        "description_en": "Agent faces difficulties with KYC/documentation requirements.",
        "description_hi": "Agent ko KYC aur documentation requirements mein dikkat hoti hai.",
        "detection_hints": [
            "KYC", "document", "Aadhaar", "PAN", "verification",
            "identity", "proof",
            "documents", "Aadhaar nahi", "PAN card", "verification fail",
        ],
        "suggested_playbook": "operational_kyc_support",
        "suggested_action_en": "Provide KYC checklist and help with document collection process",
        "suggested_action_hi": "KYC checklist dein aur document collection mein madad karein",
        "adm_talking_points": [
            "Clarify exactly which documents are needed",
            "Help identify alternatives if standard documents are unavailable",
            "Share a simple KYC document collection checklist",
        ],
    },

    # ===== PERSONAL (5 reasons) ============================================
    {
        "code": DormancyReasonCode.HEALTH_ISSUES,
        "category": DormancyReasonCategory.PERSONAL,
        "name_en": "Health Issues",
        "name_hi": "Tabiyat kharab hai",
        "description_en": "Agent is dealing with health problems that prevent active work.",
        "description_hi": "Agent ki tabiyat kharab hai aur woh kaam nahi kar pa raha.",
        "detection_hints": [
            "health", "sick", "hospital", "medical", "unwell",
            "treatment", "surgery",
            "bimaar", "hospital", "tabiyat", "doctor",
        ],
        "suggested_playbook": "personal_health_support",
        "suggested_action_en": "Express empathy; offer flexible re-engagement when they are ready",
        "suggested_action_hi": "Hamdardi jatayein; jab theek hon tab flexible re-engagement offer karein",
        "adm_talking_points": [
            "Express genuine concern for their health first",
            "Do NOT push for business — just check in",
            "Offer to help when they feel ready, with no pressure",
        ],
    },
    {
        "code": DormancyReasonCode.RELOCATED,
        "category": DormancyReasonCategory.PERSONAL,
        "name_en": "Relocated",
        "name_hi": "Doosri jagah shift ho gaye",
        "description_en": "Agent has moved to a different location and lost their network.",
        "description_hi": "Agent doosri jagah shift ho gaye hain aur unka network chala gaya.",
        "detection_hints": [
            "moved", "relocated", "shifting", "new city",
            "different place", "transfer",
            "shift ho gaya", "naya shahar", "chala gaya",
        ],
        "suggested_playbook": "personal_relocation_support",
        "suggested_action_en": "Connect with local ADM in new area; help rebuild network",
        "suggested_action_hi": "Naye area ke local ADM se connect karein; network rebuild mein madad karein",
        "adm_talking_points": [
            "Find out where they have moved to",
            "Introduce them to the ADM or team in the new area",
            "Help them identify warm market contacts in the new location",
        ],
    },
    {
        "code": DormancyReasonCode.FAMILY_OBLIGATIONS,
        "category": DormancyReasonCategory.PERSONAL,
        "name_en": "Family Obligations",
        "name_hi": "Family ki zimmedaari",
        "description_en": "Agent has family responsibilities limiting their availability.",
        "description_hi": "Agent ke paas family ki zimmedaariyan hain jo unka time le rahi hain.",
        "detection_hints": [
            "family", "children", "parents", "wedding", "personal",
            "home", "busy with family",
            "ghar", "bachche", "shaadi", "family mein",
        ],
        "suggested_playbook": "personal_flexible_engagement",
        "suggested_action_en": "Offer flexible working arrangements; suggest part-time strategies",
        "suggested_action_hi": "Flexible working ka option dein; part-time strategies suggest karein",
        "adm_talking_points": [
            "Understand their situation empathetically",
            "Suggest insurance selling in their social circle as a start",
            "Propose a realistic 2-3 hours/week plan",
        ],
    },
    {
        "code": DormancyReasonCode.LOST_INTEREST,
        "category": DormancyReasonCategory.PERSONAL,
        "name_en": "Lost Interest",
        "name_hi": "Interest khatam ho gaya",
        "description_en": "Agent has lost interest in insurance as a career.",
        "description_hi": "Agent ka insurance mein interest khatam ho gaya hai.",
        "detection_hints": [
            "not interested", "lost interest", "boring", "don't want",
            "quit", "leave", "give up",
            "interest nahi", "chhod dena hai", "mann nahi hai",
        ],
        "suggested_playbook": "personal_reengagement_motivation",
        "suggested_action_en": "Understand root cause; share success stories; reconnect with original motivation",
        "suggested_action_hi": "Root cause samjhein; success stories share karein; original motivation se reconnect karein",
        "adm_talking_points": [
            "Ask what originally attracted them to insurance",
            "Share inspiring success stories of agents who felt the same way",
            "Explore if there is a specific trigger that caused the disinterest",
        ],
    },
    {
        "code": DormancyReasonCode.OTHER_EMPLOYMENT,
        "category": DormancyReasonCategory.PERSONAL,
        "name_en": "Other Employment",
        "name_hi": "Doosri naukri kar rahe hain",
        "description_en": "Agent has taken up another job (full-time or part-time).",
        "description_hi": "Agent ne doosri naukri le li hai (full-time ya part-time).",
        "detection_hints": [
            "another job", "other work", "employment", "office job",
            "shop", "business", "full-time",
            "doosra kaam", "naukri", "job lag gayi", "dukaan",
        ],
        "suggested_playbook": "personal_parttime_engagement",
        "suggested_action_en": "Position insurance as supplementary income; suggest weekend/evening strategies",
        "suggested_action_hi": "Insurance ko supplementary income ke taur pe position karein",
        "adm_talking_points": [
            "Congratulate them on the new opportunity",
            "Explore if they can do insurance part-time (weekends, evenings)",
            "Show how even 2-3 policies a month can add good income",
        ],
    },

    # ===== REGULATORY (3 reasons) ==========================================
    {
        "code": DormancyReasonCode.LICENSE_EXPIRED,
        "category": DormancyReasonCategory.REGULATORY,
        "name_en": "License Expired",
        "name_hi": "License expire ho gaya",
        "description_en": "Agent's IRDAI license has expired and they cannot sell.",
        "description_hi": "Agent ka IRDAI license expire ho gaya hai aur woh sell nahi kar sakta.",
        "detection_hints": [
            "license expired", "IRDAI", "cannot sell", "expired",
            "renewal", "lapsed license",
            "license khatam", "expire", "nahi bech sakta",
        ],
        "suggested_playbook": "regulatory_license_renewal",
        "suggested_action_en": "Urgent: help with license renewal process and training hour completion",
        "suggested_action_hi": "Urgent: license renewal process aur training hours complete karne mein madad karein",
        "adm_talking_points": [
            "Explain the renewal process clearly step by step",
            "Help calculate remaining training hours needed",
            "Offer to help schedule training sessions immediately",
        ],
    },
    {
        "code": DormancyReasonCode.LICENSE_EXPIRING_SOON,
        "category": DormancyReasonCategory.REGULATORY,
        "name_en": "License Expiring Soon",
        "name_hi": "License jaldi expire hone wala hai",
        "description_en": "Agent's license will expire within 60 days.",
        "description_hi": "Agent ka license 60 dinon mein expire hone wala hai.",
        "detection_hints": [
            "expiring", "renew", "license renewal", "training hours",
            "CPD", "continuing education",
            "expire hone wala", "renew karna hai", "training hours baaki",
        ],
        "suggested_playbook": "regulatory_license_renewal",
        "suggested_action_en": "Start renewal training immediately and track progress daily",
        "suggested_action_hi": "Renewal training turant shuru karein aur daily progress track karein",
        "adm_talking_points": [
            "Create urgency without creating panic",
            "Break down the training requirement into daily targets",
            "Check in every 3 days on progress",
        ],
    },
    {
        "code": DormancyReasonCode.COMPLIANCE_ISSUE,
        "category": DormancyReasonCategory.REGULATORY,
        "name_en": "Compliance Issue",
        "name_hi": "Compliance ki problem",
        "description_en": "Agent has compliance issues (mis-selling complaint, regulatory action).",
        "description_hi": "Agent ke compliance issues hain (mis-selling complaint, regulatory action).",
        "detection_hints": [
            "compliance", "mis-selling", "complaint", "IRDAI action",
            "penalty", "fine",
            "complaint aaya", "galat selling", "penalty",
        ],
        "suggested_playbook": "regulatory_compliance_resolution",
        "suggested_action_en": "Review compliance issue carefully; provide corrective training",
        "suggested_action_hi": "Compliance issue carefully review karein; corrective training dein",
        "adm_talking_points": [
            "Understand the specific compliance concern without being judgmental",
            "Explain what needs to happen to resolve the issue",
            "Provide compliance refresher training",
        ],
    },

    # ===== UNKNOWN (1 reason) ==============================================
    {
        "code": DormancyReasonCode.UNKNOWN,
        "category": DormancyReasonCategory.UNKNOWN,
        "name_en": "Unknown",
        "name_hi": "Wajah pata nahi",
        "description_en": "Dormancy reason not yet identified. Needs direct conversation.",
        "description_hi": "Dormancy ki wajah abhi pata nahi hai. Direct conversation zaruri hai.",
        "detection_hints": [],
        "suggested_playbook": "generic_reengagement",
        "suggested_action_en": "Reach out with a friendly check-in to understand the situation",
        "suggested_action_hi": "Friendly check-in call karein taaki situation samajh aaye",
        "adm_talking_points": [
            "Start with a warm, non-judgmental check-in",
            "Ask open-ended questions about how they are doing",
            "Listen more than talk — the goal is to understand, not to pitch",
        ],
    },
]


# ---------------------------------------------------------------------------
# Lookup Helpers
# ---------------------------------------------------------------------------

# Build fast-lookup indexes
_CODE_INDEX: dict[str, dict] = {r["code"]: r for r in DORMANCY_TAXONOMY}
_CATEGORY_INDEX: dict[str, list[dict]] = {}
for _reason in DORMANCY_TAXONOMY:
    _cat = _reason["category"]
    _CATEGORY_INDEX.setdefault(_cat, []).append(_reason)


def get_dormancy_taxonomy() -> list[dict]:
    """Return the full dormancy taxonomy (copy for safety)."""
    return list(DORMANCY_TAXONOMY)


def get_reason_by_code(code: str) -> dict | None:
    """Look up a single dormancy reason by its code."""
    return _CODE_INDEX.get(code)


def get_reasons_by_category(category: str) -> list[dict]:
    """Return all reasons for a given parent category."""
    return _CATEGORY_INDEX.get(category, [])


def get_category_summary() -> list[dict]:
    """Return a summary of each category with count and reason names."""
    summaries = []
    for cat in DormancyReasonCategory:
        reasons = _CATEGORY_INDEX.get(cat, [])
        summaries.append({
            "category": cat,
            "name_en": cat.replace("_", " ").title(),
            "name_hi": _CATEGORY_NAMES_HI.get(cat, cat),
            "count": len(reasons),
            "reason_codes": [r["code"] for r in reasons],
        })
    return summaries


def detect_dormancy_reason(text: str) -> list[dict]:
    """Detect possible dormancy reasons from free text (agent conversation).

    Returns a list of matching reasons sorted by number of hint matches
    (highest first). Used for initial classification that can be confirmed
    by ADM or Voice AI.

    Args:
        text: Free-text input from agent conversation (Hindi or English).

    Returns:
        List of matching reason dicts with a 'match_score' field added.
    """
    if not text:
        return []

    text_lower = text.lower()
    matches = []

    for reason in DORMANCY_TAXONOMY:
        hints = reason.get("detection_hints", [])
        if not hints:
            continue
        score = sum(1 for hint in hints if hint.lower() in text_lower)
        if score > 0:
            result = dict(reason)
            result["match_score"] = score
            matches.append(result)

    matches.sort(key=lambda r: r["match_score"], reverse=True)
    return matches


# Category display names in Hindi
_CATEGORY_NAMES_HI: dict[str, str] = {
    DormancyReasonCategory.TRAINING_GAP: "Training ki Kami",
    DormancyReasonCategory.ENGAGEMENT_GAP: "Support ki Kami",
    DormancyReasonCategory.ECONOMIC: "Paison ki Chinta",
    DormancyReasonCategory.OPERATIONAL: "Process ki Dikkat",
    DormancyReasonCategory.PERSONAL: "Personal Wajah",
    DormancyReasonCategory.REGULATORY: "License / Compliance",
    DormancyReasonCategory.UNKNOWN: "Wajah Pata Nahi",
}
