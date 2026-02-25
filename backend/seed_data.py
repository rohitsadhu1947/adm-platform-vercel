"""
Seed data for the ADM Platform.
Seeds only essential reference data: products, training modules, and an admin user.
All operational data (ADMs, agents, interactions, etc.) is created through the app.
"""

import hashlib
import logging
from sqlalchemy.orm import Session

from models import User, Product, ReasonTaxonomy

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Axis Max Life Products (real catalog)
# ---------------------------------------------------------------------------
PRODUCTS = [
    {
        "name": "Smart Term Plan",
        "category": "term",
        "description": "Pure term life insurance with high coverage at affordable premiums. Available in Regular, Limited, and Single pay options.",
        "key_features": '["Life cover up to ₹25 Cr", "Flexible payout options", "Critical illness rider available", "Premium waiver benefit", "Return of premium variant"]',
        "premium_range": "₹5,000 - ₹50,000/year",
        "commission_rate": "30-35% first year, 5% renewal",
        "target_audience": "Salaried individuals, 25-55 years",
        "selling_tips": "Focus on family protection angle. Compare with LIC term plans showing better claim ratio.",
    },
    {
        "name": "Smart Secure Plus",
        "category": "savings",
        "description": "Guaranteed savings plan with life cover. Non-linked, non-participating endowment plan with guaranteed maturity benefit.",
        "key_features": '["Guaranteed maturity benefit", "Life cover during policy term", "Tax benefits u/s 80C & 10(10D)", "Loan facility available", "Flexible premium payment terms"]',
        "premium_range": "₹25,000 - ₹5,00,000/year",
        "commission_rate": "25-30% first year, 5% renewal",
        "target_audience": "Conservative investors, 30-50 years",
        "selling_tips": "Position as safe alternative to FDs with insurance benefit. Show guaranteed return calculations.",
    },
    {
        "name": "Smart Wealth Plan",
        "category": "ulip",
        "description": "Unit Linked Insurance Plan with market-linked returns and life cover. Multiple fund options with free switches.",
        "key_features": '["Market-linked returns", "Multiple fund options", "Free switches between funds", "Partial withdrawal after 5 years", "Top-up facility"]',
        "premium_range": "₹50,000 - ₹10,00,000/year",
        "commission_rate": "8-12% of premium",
        "target_audience": "Aggressive investors, 25-45 years",
        "selling_tips": "Show long-term wealth creation potential. Compare with mutual funds highlighting insurance + investment combo.",
    },
    {
        "name": "Smart Kidz Plan",
        "category": "child",
        "description": "Child education and marriage plan with guaranteed benefits. Ensures child's financial future even in parent's absence.",
        "key_features": '["Guaranteed education fund", "Waiver of premium on parent death", "Milestone-based payouts", "Premium waiver rider", "Flexible payout age"]',
        "premium_range": "₹20,000 - ₹2,00,000/year",
        "commission_rate": "25-28% first year, 5% renewal",
        "target_audience": "Parents with children 0-12 years",
        "selling_tips": "Emotional sell - secure your child's future. Show how education costs are rising 10-12% annually.",
    },
    {
        "name": "Smart Pension Plan",
        "category": "pension",
        "description": "Retirement savings plan with guaranteed annuity. Build a retirement corpus with regular monthly pension.",
        "key_features": '["Guaranteed pension for life", "Joint life option", "Commutation up to 60%", "Death benefit to nominee", "Tax benefits on premium"]',
        "premium_range": "₹30,000 - ₹5,00,000/year",
        "commission_rate": "20-25% first year, 3% renewal",
        "target_audience": "Working professionals, 30-55 years",
        "selling_tips": "Show retirement gap analysis. Use NPS comparison to highlight guarantee advantage.",
    },
    {
        "name": "Group Term Life",
        "category": "group",
        "description": "Group insurance for businesses and organizations. Provides life cover to employees at competitive rates.",
        "key_features": '["Low per-member cost", "Easy administration", "Customizable coverage", "No medical for small groups", "Annual renewable"]',
        "premium_range": "₹500 - ₹5,000/member/year",
        "commission_rate": "15-20% of total premium",
        "target_audience": "SMEs, corporates, associations",
        "selling_tips": "Approach HR departments. Show employee retention benefits and tax deductibility for employer.",
    },
    {
        "name": "Smart Health Plan",
        "category": "health",
        "description": "Comprehensive health insurance with critical illness cover. Covers hospitalization, surgeries, and critical illnesses.",
        "key_features": '["Cashless hospitalization", "No claim bonus", "Critical illness cover", "Day care procedures", "Pre-post hospitalization"]',
        "premium_range": "₹8,000 - ₹35,000/year",
        "commission_rate": "20-25% first year, 10% renewal",
        "target_audience": "Individuals and families, 25-65 years",
        "selling_tips": "Show rising healthcare costs. Position as supplement to employer insurance for comprehensive coverage.",
    },
    {
        "name": "SWAG (Smart Wealth Advantage Guarantee)",
        "category": "savings",
        "description": "Short-term guaranteed returns plan. Premium paying term of 5-7 years with guaranteed survival benefits.",
        "key_features": '["Short premium paying term", "Guaranteed returns", "Life cover throughout", "Tax-free maturity", "Partial withdrawal option"]',
        "premium_range": "₹1,00,000 - ₹10,00,000/year",
        "commission_rate": "25-30% first year, 5% renewal",
        "target_audience": "High-income individuals seeking safe returns",
        "selling_tips": "Best for customers who want guaranteed returns with short commitment. Compare with PPF/FD showing tax advantage.",
    },
]

# ---------------------------------------------------------------------------
# Training modules
# ---------------------------------------------------------------------------
TRAINING_MODULES = [
    {"name": "Term Insurance Masterclass", "category": "product_knowledge"},
    {"name": "ULIP Fund Selection Guide", "category": "product_knowledge"},
    {"name": "Savings Plans Deep Dive", "category": "product_knowledge"},
    {"name": "Child Plan Selling Strategies", "category": "product_knowledge"},
    {"name": "Pension Products Workshop", "category": "product_knowledge"},
    {"name": "Consultative Selling Approach", "category": "sales_techniques"},
    {"name": "Objection Handling Mastery", "category": "objection_handling"},
    {"name": "IRDAI Compliance Essentials", "category": "compliance"},
    {"name": "Digital Sales Tools Training", "category": "digital_tools"},
    {"name": "Building Customer Relationships", "category": "soft_skills"},
    {"name": "Need-Based Selling", "category": "sales_techniques"},
    {"name": "Claims Process Navigation", "category": "compliance"},
]


# ---------------------------------------------------------------------------
# Feedback Reason Taxonomy (5 buckets, 35+ reasons)
# Derived from client data: 171 responses from 111 agents
# ---------------------------------------------------------------------------
REASON_TAXONOMY = [
    # --- UNDERWRITING ---
    {"code": "UW-01", "bucket": "underwriting", "reason_name": "High policy rejection rate",
     "description": "Too many proposals getting rejected in agent's district or customer segment",
     "sub_reasons": '["District-specific rejections", "Rural area rejections", "Specific age-group rejections"]',
     "keywords": '["rejection", "rejected", "proposal rejected", "declined", "not approved", "policy reject"]',
     "suggested_data_points": '["rejection_rate_district", "rejection_rate_national_avg", "affected_agents_count"]',
     "typical_sla_hours": 48, "display_order": 1},
    {"code": "UW-02", "bucket": "underwriting", "reason_name": "Premium pricing too high",
     "description": "Customers find premiums unaffordable or too expensive compared to competition",
     "sub_reasons": '["Premiums unaffordable", "No monthly EMI option", "1-year installment too large"]',
     "keywords": '["premium high", "expensive", "costly", "price", "afford", "too much", "pricing"]',
     "suggested_data_points": '["product_premium_comparison", "competitor_pricing"]',
     "typical_sla_hours": 72, "display_order": 2},
    {"code": "UW-03", "bucket": "underwriting", "reason_name": "Medical underwriting too strict",
     "description": "Excessive medical tests or age-based restrictions turning away customers",
     "sub_reasons": '["Excessive medical tests", "Age-based restrictions", "Pre-existing condition rejections"]',
     "keywords": '["medical", "test", "health check", "pre-existing", "medical exam", "medicals"]',
     "suggested_data_points": '["medical_requirement_matrix", "age_based_rejection_rate"]',
     "typical_sla_hours": 48, "display_order": 3},
    {"code": "UW-04", "bucket": "underwriting", "reason_name": "NRI / special case processing",
     "description": "NRI or special cases stuck in processing with excessive documentation requirements",
     "sub_reasons": '["NRI cases stuck", "Tax benefit issues for NRI", "Documentation overload"]',
     "keywords": '["NRI", "non-resident", "special case", "foreign", "abroad"]',
     "suggested_data_points": '["nri_processing_time", "pending_nri_cases"]',
     "typical_sla_hours": 72, "display_order": 4},
    {"code": "UW-05", "bucket": "underwriting", "reason_name": "Proposal stuck in UW queue",
     "description": "Long processing times with no status updates on submitted proposals",
     "sub_reasons": '["Long processing times", "No status updates", "Proposals pending for weeks"]',
     "keywords": '["stuck", "pending", "waiting", "processing", "queue", "delay", "no update"]',
     "suggested_data_points": '["avg_processing_time", "pending_proposals_count"]',
     "typical_sla_hours": 24, "display_order": 5},
    {"code": "UW-06", "bucket": "underwriting", "reason_name": "Eligibility criteria too narrow",
     "description": "Income proof or occupation restrictions excluding potential customers",
     "sub_reasons": '["Income proof requirements too strict", "Occupation restrictions", "Rural customer exclusion"]',
     "keywords": '["eligibility", "criteria", "not eligible", "income proof", "occupation", "rural"]',
     "suggested_data_points": '["eligibility_criteria_comparison", "excluded_segment_size"]',
     "typical_sla_hours": 72, "display_order": 6},
    {"code": "UW-07", "bucket": "underwriting", "reason_name": "Counter-offer dissatisfaction",
     "description": "Sum assured reduced or riders removed or premium loaded without explanation",
     "sub_reasons": '["Sum assured reduced", "Riders removed", "Premium loaded without explanation"]',
     "keywords": '["counter offer", "counter-offer", "reduced", "loaded", "rider removed"]',
     "suggested_data_points": '["counter_offer_rate", "counter_offer_acceptance_rate"]',
     "typical_sla_hours": 48, "display_order": 7},

    # --- FINANCE ---
    {"code": "FIN-01", "bucket": "finance", "reason_name": "Commission not paid on time",
     "description": "Delayed commission payouts with no clarity on timeline",
     "sub_reasons": '["Delayed payout", "Pending for months", "No clarity on timeline"]',
     "keywords": '["commission delay", "not paid", "payout delay", "payment pending", "commission late"]',
     "suggested_data_points": '["avg_payout_time", "pending_commissions_count"]',
     "typical_sla_hours": 24, "display_order": 1},
    {"code": "FIN-02", "bucket": "finance", "reason_name": "Commission amount disputed",
     "description": "Commission lower than expected or calculation unclear",
     "sub_reasons": '["Lower than expected", "Calculation unclear", "Deductions unexplained"]',
     "keywords": '["commission less", "commission wrong", "calculation", "deducted", "disputed"]',
     "suggested_data_points": '["commission_calculation_breakdown", "policy_commission_details"]',
     "typical_sla_hours": 48, "display_order": 2},
    {"code": "FIN-03", "bucket": "finance", "reason_name": "Commission stuck / blocked",
     "description": "Large commission amounts stuck for extended periods with no resolution",
     "sub_reasons": '["Large amounts stuck for years", "No resolution despite follow-ups"]',
     "keywords": '["commission stuck", "blocked", "held", "frozen", "not released"]',
     "suggested_data_points": '["stuck_amount", "duration_stuck", "case_history"]',
     "typical_sla_hours": 24, "display_order": 3},
    {"code": "FIN-04", "bucket": "finance", "reason_name": "Persistency clawback",
     "description": "Commission reversed due to customer policy lapse, perceived as unfair",
     "sub_reasons": '["Commission reversed due to lapse", "Unfair recovery", "No warning before clawback"]',
     "keywords": '["clawback", "persistency", "reversed", "recovery", "lapse", "deducted back"]',
     "suggested_data_points": '["clawback_amount", "lapse_rate", "persistency_ratio"]',
     "typical_sla_hours": 48, "display_order": 4},
    {"code": "FIN-05", "bucket": "finance", "reason_name": "Low commission rates",
     "description": "Commission on small ticket policies too low to be worthwhile",
     "sub_reasons": '["Small ticket negligible commission", "Not worth the effort", "Lower than competitor rates"]',
     "keywords": '["low commission", "commission rate", "not worth", "too little", "earning less"]',
     "suggested_data_points": '["commission_rate_comparison", "avg_ticket_size"]',
     "typical_sla_hours": 72, "display_order": 5},
    {"code": "FIN-06", "bucket": "finance", "reason_name": "Contest prize not received",
     "description": "Met contest criteria but prize/reward not distributed",
     "sub_reasons": '["Met criteria but no payout", "Delayed prize distribution", "Prize amount incorrect"]',
     "keywords": '["contest prize", "reward not received", "incentive", "prize pending"]',
     "suggested_data_points": '["contest_name", "qualification_proof", "prize_status"]',
     "typical_sla_hours": 48, "display_order": 6},
    {"code": "FIN-07", "bucket": "finance", "reason_name": "Incentive structure unclear",
     "description": "Agent doesn't understand how commission and incentives are calculated",
     "sub_reasons": '["Calculation not transparent", "No documentation provided", "Rules keep changing"]',
     "keywords": '["unclear", "dont understand", "how calculated", "no transparency", "incentive structure"]',
     "suggested_data_points": '["commission_structure_doc", "recent_changes"]',
     "typical_sla_hours": 48, "display_order": 7},
    {"code": "FIN-08", "bucket": "finance", "reason_name": "Tax deduction issues",
     "description": "TDS too high or no proper tax documentation provided",
     "sub_reasons": '["TDS too high", "No proper tax documentation", "Form 16A not issued"]',
     "keywords": '["TDS", "tax", "deduction", "Form 16", "tax certificate"]',
     "suggested_data_points": '["tds_rate", "form16_status"]',
     "typical_sla_hours": 72, "display_order": 8},

    # --- CONTEST & ENGAGEMENT ---
    {"code": "CON-01", "bucket": "contest", "reason_name": "Insufficient contests",
     "description": "Not enough motivation programs or only for top performers",
     "sub_reasons": '["Not enough programs", "Only for top performers", "No small-ticket contests"]',
     "keywords": '["no contest", "no program", "no motivation", "no incentive program", "no reward"]',
     "suggested_data_points": '["active_contests", "agent_participation_rate"]',
     "typical_sla_hours": 72, "display_order": 1},
    {"code": "CON-02", "bucket": "contest", "reason_name": "Contest criteria unfair",
     "description": "Contest rules too high or changed midway through the contest period",
     "sub_reasons": '["Rules changed midway", "Criteria too high for part-time agents", "Unfair criteria"]',
     "keywords": '["contest unfair", "criteria", "rules changed", "too high target", "not achievable"]',
     "suggested_data_points": '["contest_rules", "participation_vs_completion"]',
     "typical_sla_hours": 48, "display_order": 2},
    {"code": "CON-03", "bucket": "contest", "reason_name": "Contest prize not honoured",
     "description": "Agent completed requirements but prize/recognition not given",
     "sub_reasons": '["Requirements met but no prize", "Partial prize given", "Different prize than promised"]',
     "keywords": '["prize not given", "not honoured", "didnt receive", "contest cheat"]',
     "suggested_data_points": '["contest_qualification_data", "prize_distribution_status"]',
     "typical_sla_hours": 48, "display_order": 3},
    {"code": "CON-04", "bucket": "contest", "reason_name": "No recognition program",
     "description": "No appreciation for consistent performers, only big cases celebrated",
     "sub_reasons": '["No small performer recognition", "Only big cases celebrated", "No milestone awards"]',
     "keywords": '["recognition", "appreciation", "no reward", "not recognized", "ignored"]',
     "suggested_data_points": '["agent_performance_history", "recognition_programs"]',
     "typical_sla_hours": 72, "display_order": 4},
    {"code": "CON-05", "bucket": "contest", "reason_name": "Engagement gap with office",
     "description": "No regular contact from office, agent feels disconnected",
     "sub_reasons": '["No regular contact", "Office does not reach out", "Feel disconnected"]',
     "keywords": '["no contact", "disconnected", "no support", "nobody calls", "forgotten"]',
     "suggested_data_points": '["last_contact_date", "adm_interaction_frequency"]',
     "typical_sla_hours": 48, "display_order": 5},
    {"code": "CON-06", "bucket": "contest", "reason_name": "No re-engagement programs",
     "description": "No specific programs to bring back inactive agents",
     "sub_reasons": '["No comeback programs", "No reactivation incentives", "No bridge training"]',
     "keywords": '["no program for inactive", "comeback", "reactivation", "re-engagement"]',
     "suggested_data_points": '["reactivation_programs_available", "similar_agent_success_stories"]',
     "typical_sla_hours": 72, "display_order": 6},
    {"code": "CON-07", "bucket": "contest", "reason_name": "Training schedule mismatch",
     "description": "Training only available at inconvenient times or locations",
     "sub_reasons": '["Only morning training", "Need evening/weekend options", "Online preferred"]',
     "keywords": '["training time", "training schedule", "cant attend", "no online", "timing"]',
     "suggested_data_points": '["training_schedule", "online_training_availability"]',
     "typical_sla_hours": 72, "display_order": 7},
    {"code": "CON-08", "bucket": "contest", "reason_name": "No marketing material",
     "description": "No brochures or digital material to share with prospects",
     "sub_reasons": '["No brochures", "No digital material", "No social media content"]',
     "keywords": '["brochure", "material", "pamphlet", "digital content", "marketing"]',
     "suggested_data_points": '["available_marketing_materials", "digital_tools"]',
     "typical_sla_hours": 72, "display_order": 8},

    # --- OPERATIONS ---
    {"code": "OPS-01", "bucket": "operations", "reason_name": "Policy issuance failures",
     "description": "Policy generation errors or stuck in processing after payment",
     "sub_reasons": '["Policy generation errors", "Stuck after payment", "Issuance delays"]',
     "keywords": '["policy issuance", "policy not issued", "generation failed", "issuance error"]',
     "suggested_data_points": '["issuance_failure_rate", "pending_issuance_count"]',
     "typical_sla_hours": 24, "display_order": 1},
    {"code": "OPS-02", "bucket": "operations", "reason_name": "Payment gateway failures",
     "description": "Customer payment fails during purchase, UPI/card issues",
     "sub_reasons": '["Customer payment fails", "Retry issues", "UPI/card failures"]',
     "keywords": '["payment fail", "PG failure", "gateway", "UPI", "card declined", "payment issue"]',
     "suggested_data_points": '["pg_failure_rate", "affected_payment_methods"]',
     "typical_sla_hours": 4, "display_order": 2},
    {"code": "OPS-03", "bucket": "operations", "reason_name": "App / system not working",
     "description": "Login issues, app crashes, slow performance",
     "sub_reasons": '["Login issues", "App crashes", "Slow performance", "System down"]',
     "keywords": '["app", "system", "login", "crash", "not working", "down", "error", "portal"]',
     "suggested_data_points": '["system_uptime", "known_issues", "fix_timeline"]',
     "typical_sla_hours": 4, "display_order": 3},
    {"code": "OPS-04", "bucket": "operations", "reason_name": "Cumbersome digital journey",
     "description": "Too many steps, not mobile-friendly, document upload problems",
     "sub_reasons": '["Too many steps", "Not mobile-friendly", "Document upload issues"]',
     "keywords": '["digital journey", "too many steps", "complicated", "upload", "mobile"]',
     "suggested_data_points": '["journey_step_count", "drop_off_rate"]',
     "typical_sla_hours": 72, "display_order": 4},
    {"code": "OPS-05", "bucket": "operations", "reason_name": "Payout processing delays",
     "description": "System delays in processing agent payouts and settlements",
     "sub_reasons": '["System delays", "Batch processing issues", "Settlement failures"]',
     "keywords": '["payout delay", "processing delay", "settlement", "not credited"]',
     "suggested_data_points": '["avg_payout_processing_time", "pending_payouts"]',
     "typical_sla_hours": 24, "display_order": 5},
    {"code": "OPS-06", "bucket": "operations", "reason_name": "Customer portal issues",
     "description": "Customers can't access policy details or make premium payments",
     "sub_reasons": '["Cannot access policy details", "Premium payment issues online", "Portal errors"]',
     "keywords": '["customer portal", "customer login", "customer access", "customer app"]',
     "suggested_data_points": '["customer_portal_uptime", "reported_issues"]',
     "typical_sla_hours": 24, "display_order": 6},
    {"code": "OPS-07", "bucket": "operations", "reason_name": "Surrender / modification issues",
     "description": "Policy surrender or modification process complicated or stuck",
     "sub_reasons": '["Surrender process complicated", "Modification requests stuck", "Long wait times"]',
     "keywords": '["surrender", "modification", "change", "cancel", "alter"]',
     "suggested_data_points": '["surrender_processing_time", "pending_modifications"]',
     "typical_sla_hours": 48, "display_order": 7},
    {"code": "OPS-08", "bucket": "operations", "reason_name": "Communication system failures",
     "description": "SMS/email notifications not reaching customers or agents",
     "sub_reasons": '["SMS not received", "Email failures", "Notification issues"]',
     "keywords": '["SMS", "email", "notification", "not received", "communication"]',
     "suggested_data_points": '["delivery_rate", "failure_logs"]',
     "typical_sla_hours": 24, "display_order": 8},

    # --- PRODUCT ---
    {"code": "PRD-01", "bucket": "product", "reason_name": "Products too complex",
     "description": "Hard to explain to customers, too many riders and options",
     "sub_reasons": '["Hard to explain", "Too many riders/options", "Customers get confused"]',
     "keywords": '["complex", "complicated", "hard to explain", "confusing", "too many options"]',
     "suggested_data_points": '["product_simplification_initiatives", "training_materials"]',
     "typical_sla_hours": 72, "display_order": 1},
    {"code": "PRD-02", "bucket": "product", "reason_name": "Competitor products better",
     "description": "Other companies offer better returns, lower premiums, or simpler products",
     "sub_reasons": '["Better returns elsewhere", "Lower premiums at competitor", "Simpler competitor products"]',
     "keywords": '["competitor", "LIC", "HDFC", "SBI", "better", "cheaper", "other company"]',
     "suggested_data_points": '["competitive_analysis", "product_comparison"]',
     "typical_sla_hours": 72, "display_order": 2},
    {"code": "PRD-03", "bucket": "product", "reason_name": "No low ticket size products",
     "description": "Customers want monthly 500-1000 premium products, minimum premium too high",
     "sub_reasons": '["Minimum premium too high", "No micro-insurance", "No monthly 500-1000 options"]',
     "keywords": '["low ticket", "small premium", "affordable", "minimum premium", "micro"]',
     "suggested_data_points": '["minimum_premium_by_product", "micro_insurance_plans"]',
     "typical_sla_hours": 72, "display_order": 3},
    {"code": "PRD-04", "bucket": "product", "reason_name": "Customers prefer online",
     "description": "Customers research online and buy direct, agent feels disintermediated",
     "sub_reasons": '["Customers buy online", "Agent feels bypassed", "Digital-first customers"]',
     "keywords": '["online", "direct", "internet", "digital", "website", "disintermediated"]',
     "suggested_data_points": '["online_vs_agent_sales_ratio", "agent_digital_tools"]',
     "typical_sla_hours": 72, "display_order": 4},
    {"code": "PRD-05", "bucket": "product", "reason_name": "Limited product range",
     "description": "Missing product categories like health, short-term, or micro-insurance",
     "sub_reasons": '["No health insurance", "No short-term plans", "No micro-insurance"]',
     "keywords": '["limited", "no health", "no short term", "range", "missing product"]',
     "suggested_data_points": '["product_catalog", "upcoming_products"]',
     "typical_sla_hours": 72, "display_order": 5},
    {"code": "PRD-06", "bucket": "product", "reason_name": "Product-market mismatch",
     "description": "Products don't suit rural or agriculture-income customers",
     "sub_reasons": '["Rural customers need different products", "Agriculture-income underserved", "Regional mismatch"]',
     "keywords": '["rural", "agriculture", "farmer", "mismatch", "not suitable", "village"]',
     "suggested_data_points": '["rural_customer_profile", "suitable_products"]',
     "typical_sla_hours": 72, "display_order": 6},
    {"code": "PRD-07", "bucket": "product", "reason_name": "Maturity / returns complaints",
     "description": "Customers unhappy with maturity value or expected higher returns",
     "sub_reasons": '["Maturity value low", "Expected higher returns", "Return complaints"]',
     "keywords": '["maturity", "returns", "low return", "expected more", "disappointed"]',
     "suggested_data_points": '["maturity_value_comparison", "return_projections"]',
     "typical_sla_hours": 48, "display_order": 7},
    {"code": "PRD-08", "bucket": "product", "reason_name": "Mis-selling legacy issues",
     "description": "Past mis-sold policies eroding trust, agents blamed for company issues",
     "sub_reasons": '["Past mis-sold policies", "Trust erosion", "Agents blamed for company issues"]',
     "keywords": '["mis-sell", "mis-sold", "trust", "cheated", "wrong product", "blame"]',
     "suggested_data_points": '["mis-selling_complaint_data", "remediation_programs"]',
     "typical_sla_hours": 48, "display_order": 8},
]


def _hash_password(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def seed_database(db: Session):
    """Seed the database with essential reference data only."""
    logger.info("Starting database seeding (reference data only)...")

    # Check if products already exist
    existing = db.query(Product).count()
    if existing > 0:
        logger.info(f"Database already has {existing} products. Skipping seed.")
        return

    # ------------------------------------------------------------------
    # 1. Products
    # ------------------------------------------------------------------
    products = []
    for p_data in PRODUCTS:
        product = Product(**p_data)
        db.add(product)
        products.append(product)
    db.flush()
    logger.info(f"Created {len(products)} products")

    # ------------------------------------------------------------------
    # 2. Reason Taxonomy (feedback classification reference data)
    # ------------------------------------------------------------------
    existing_reasons = db.query(ReasonTaxonomy).count()
    if existing_reasons == 0:
        for r_data in REASON_TAXONOMY:
            reason = ReasonTaxonomy(**r_data)
            db.add(reason)
        db.flush()
        logger.info(f"Created {len(REASON_TAXONOMY)} reason taxonomy entries")
    else:
        logger.info(f"Database has {existing_reasons} reason taxonomy entries. Skipping.")

    # ------------------------------------------------------------------
    # 3. Admin user (platform admin for web dashboard)
    # ------------------------------------------------------------------
    existing_admin = db.query(User).filter(User.username == "admin").first()
    if not existing_admin:
        admin_user = User(
            username="admin",
            password_hash=_hash_password("admin123"),
            role="admin",
            name="Platform Admin",
            adm_id=None,
        )
        db.add(admin_user)
        db.flush()
        logger.info("Created admin user (admin/admin123)")

    # ------------------------------------------------------------------
    # 4. Rohit Sadhu - Primary ADM with web login + Telegram linked
    # ------------------------------------------------------------------
    from models import ADM
    existing_rohit = db.query(User).filter(User.username == "rohit").first()
    if not existing_rohit:
        rohit_adm = ADM(
            name="Rohit Sadhu",
            phone="7303474258",
            region="North",
            language="Hindi,English",
            max_capacity=50,
            performance_score=0.0,
            telegram_chat_id="8321786545",
        )
        db.add(rohit_adm)
        db.flush()

        rohit_user = User(
            username="rohit",
            password_hash=_hash_password("rohit123"),
            role="adm",
            name="Rohit Sadhu",
            adm_id=rohit_adm.id,
        )
        db.add(rohit_user)
        db.flush()
        logger.info("Created ADM: Rohit Sadhu (rohit/rohit123, TG: 8321786545)")

    # ------------------------------------------------------------------
    # Commit
    # ------------------------------------------------------------------
    db.commit()
    logger.info("Database seeding completed!")
    logger.info(f"  Products: {len(products)}")
    logger.info(f"  Reason taxonomy: {len(REASON_TAXONOMY)} entries")
    logger.info("  Admin user: admin/admin123")
    logger.info("  ADM user: rohit/rohit123")
    logger.info("  Note: Additional ADMs and agents can be added via Telegram bot or web.")
