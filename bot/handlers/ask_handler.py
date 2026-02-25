"""
AI Product Q&A conversation handler for the ADM Platform Telegram Bot.
Accepts free-text questions about Axis Max Life insurance products and returns
rich, helpful answers. Supports Hindi and English naturally.

This is the ADM's (and agent's) go-to tool for quick product info, selling tips,
objection handling, and claim/process queries.
"""

import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from bot_config import AskStates
from utils.api_client import api_client
from utils.formatters import (
    format_product_answer,
    error_generic,
    error_not_registered,
    cancelled,
    header,
    section_divider,
    E_BRAIN, E_BULB, E_CHECK, E_CROSS, E_SPARKLE,
    E_BOOK, E_STAR, E_SHIELD, E_FIRE, E_CHAT,
    E_WARNING, E_PENCIL, E_LINK, E_ROCKET,
    E_THUMBSUP, E_TARGET, E_PERSON, E_PIN,
    E_MONEY, E_CHART, E_MEMO, E_CALENDAR,
    E_PHONE, E_TROPHY, E_CLOCK,
)
from utils.voice import send_voice_response

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Comprehensive Axis Max Life product knowledge base
# ---------------------------------------------------------------------------
PRODUCT_KNOWLEDGE = {
    # --- TERM INSURANCE ---
    "term": {
        "answer": (
            f"{E_SHIELD} <b>Axis Max Life Term Plans</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Term insurance sabse affordable life cover hai - pure protection,\n"
            f"no savings component. Agar insured ki death hoti hai toh nominee\n"
            f"ko lump-sum milta hai.\n\n"
            f"{E_STAR} <b>Axis Max Life Smart Term Plan:</b>\n"
            f"  {E_CHECK} Cover: Rs 25 Lakh to Rs 10 Crore\n"
            f"  {E_CHECK} Entry age: 18-65 years\n"
            f"  {E_CHECK} Premium: Rs 595/month for Rs 1 Cr (25 yrs, non-smoker)\n"
            f"  {E_CHECK} Online discount available\n"
            f"  {E_CHECK} Option to add Critical Illness cover\n\n"
            f"{E_STAR} <b>Axis Max Life Flexi Term Plan:</b>\n"
            f"  {E_CHECK} Flexible payout options (lump-sum + monthly income)\n"
            f"  {E_CHECK} Increasing cover option to beat inflation\n"
            f"  {E_CHECK} Return of premium variant available\n\n"
            f"{E_BULB} <b>Selling Tips:</b>\n"
            f"  {E_PIN} 'Ek cup chai ki keemat mein Rs 1 Cr ka cover!'\n"
            f"  {E_PIN} Young age mein lo toh premium low hota hai forever\n"
            f"  {E_PIN} Section 80C tax benefit on premiums\n\n"
            f"{E_FIRE} <b>Objection Handling:</b>\n"
            f"  Q: 'Paisa waapas nahi milta toh kya fayda?'\n"
            f"  A: 'Car insurance mein bhi paisa waapas nahi milta - protection ke liye lete hain. Rs 20/day mein family secure hai!'"
        ),
        "keywords": ["term", "term plan", "term insurance", "pure protection", "death benefit", "smart term", "flexi term", "life cover"],
    },

    # --- ULIP ---
    "ulip": {
        "answer": (
            f"{E_CHART} <b>Axis Max Life ULIP Plans</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"ULIP = Insurance + Investment. Premium ka ek hissa life cover\n"
            f"mein jaata hai, baaki market mein invest hota hai.\n\n"
            f"{E_STAR} <b>Key Products:</b>\n"
            f"  {E_CHECK} <b>Growth Maximiser Plan:</b> Market-linked returns, 4 fund options\n"
            f"  {E_CHECK} <b>Smart Wealth Plan:</b> Wealth creation + protection\n"
            f"  {E_CHECK} <b>Online Advantage Plan:</b> Low charges, 100% premium allocation\n\n"
            f"{E_BULB} <b>Features:</b>\n"
            f"  {E_PIN} 5-year lock-in period (mandatory by IRDAI)\n"
            f"  {E_PIN} Free fund switching (4-5 switches/year)\n"
            f"  {E_PIN} Loyalty additions after 5th/10th year\n"
            f"  {E_PIN} Tax-free maturity under Section 10(10D)\n"
            f"  {E_PIN} Min premium: Rs 3,000/month\n\n"
            f"{E_FIRE} <b>Selling Tips:</b>\n"
            f"  {E_PIN} 'Mutual fund + insurance ek saath'\n"
            f"  {E_PIN} Compare with FD returns over 10-15 years\n"
            f"  {E_PIN} Show historical NAV performance charts\n\n"
            f"{E_WARNING} <b>Important:</b> Always explain market risk clearly!"
        ),
        "keywords": ["ulip", "unit linked", "market linked", "investment plan", "fund", "growth maximiser", "smart wealth", "online advantage", "nav"],
    },

    # --- SAVINGS / ENDOWMENT ---
    "savings": {
        "answer": (
            f"{E_MONEY} <b>Axis Max Life Savings Plans</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Guaranteed returns chahiye toh savings/endowment plans best hain.\n"
            f"Insurance + guaranteed maturity benefit.\n\n"
            f"{E_STAR} <b>Key Products:</b>\n\n"
            f"  {E_CHECK} <b>Guaranteed Savings Plan (GSP):</b>\n"
            f"    - Guaranteed maturity payout (no market risk)\n"
            f"    - 10/12/15/20 year premium payment terms\n"
            f"    - Life cover throughout the term\n"
            f"    - Returns: ~5.5-6.5% IRR (guaranteed)\n\n"
            f"  {E_CHECK} <b>Smart Wealth Plan:</b>\n"
            f"    - Accruing guaranteed additions every year\n"
            f"    - Flexible payout options at maturity\n"
            f"    - Loan facility available after 3 years\n\n"
            f"  {E_CHECK} <b>Lifetime Assured Savings Plan:</b>\n"
            f"    - Whole life protection\n"
            f"    - Annual cash bonuses\n\n"
            f"{E_FIRE} <b>Selling Tips:</b>\n"
            f"  {E_PIN} 'FD se zyada returns + life cover FREE'\n"
            f"  {E_PIN} Guaranteed = no tension, no market risk\n"
            f"  {E_PIN} Best for risk-averse customers (homemakers, seniors)"
        ),
        "keywords": ["savings", "saving plan", "endowment", "guaranteed", "gsp", "guaranteed savings", "assured savings", "maturity", "guaranteed return"],
    },

    # --- CHILD PLANS ---
    "child": {
        "answer": (
            f"{E_STAR} <b>Axis Max Life Child Plans</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Bachche ke future ke liye - education, marriage, career.\n\n"
            f"{E_CHECK} <b>Axis Max Life Secure Child Plan:</b>\n"
            f"  {E_PIN} Premium payment: 10-20 years\n"
            f"  {E_PIN} Maturity: When child reaches 18-25 years\n"
            f"  {E_PIN} Premium waiver on parent's death\n"
            f"  {E_PIN} Guaranteed additions every year\n"
            f"  {E_PIN} Partial withdrawals for milestones\n\n"
            f"{E_CHECK} <b>Young India Plan:</b>\n"
            f"  {E_PIN} Market-linked growth (ULIP type)\n"
            f"  {E_PIN} Higher return potential for longer tenure\n\n"
            f"{E_BULB} <b>Key Selling Point:</b>\n"
            f"  'Aaj Rs 5,000/month se shuru karo, bachche ko 18 saal mein\n"
            f"  Rs 25 Lakh+ milega - chahe kuch bhi ho!'\n\n"
            f"{E_FIRE} <b>Emotional Hook:</b>\n"
            f"  'Aap rahen ya na rahen, bachche ka sapna poora hoga'"
        ),
        "keywords": ["child", "bachcha", "bachche", "children", "education", "young india", "secure child", "kids", "child plan", "bacchon"],
    },

    # --- RETIREMENT / PENSION ---
    "retirement": {
        "answer": (
            f"{E_CALENDAR} <b>Axis Max Life Retirement Plans</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Retirement planning - pension ke liye regular income.\n\n"
            f"{E_CHECK} <b>Axis Max Life Forever Young Pension Plan:</b>\n"
            f"  {E_PIN} Guaranteed pension for life after retirement\n"
            f"  {E_PIN} Premium payment: 5/8/10/12 years\n"
            f"  {E_PIN} Annuity starts at chosen retirement age\n"
            f"  {E_PIN} Joint life option with spouse\n"
            f"  {E_PIN} Return of purchase price to nominee\n\n"
            f"{E_CHECK} <b>Retirement Savings Plan:</b>\n"
            f"  {E_PIN} Accumulation + Pension phase\n"
            f"  {E_PIN} Vesting age: 45-75 years\n"
            f"  {E_PIN} Tax benefits under Section 80CCC\n\n"
            f"{E_BULB} <b>Selling Tips:</b>\n"
            f"  {E_PIN} 'Monthly Rs 10,000 invest karo, 60 ke baad Rs 50,000+/month pension!'\n"
            f"  {E_PIN} Show power of compounding over 20-25 years\n"
            f"  {E_PIN} NPS comparison - insurance gives guaranteed option"
        ),
        "keywords": ["retirement", "pension", "forever young", "annuity", "retire", "old age", "budhape"],
    },

    # --- HEALTH / CRITICAL ILLNESS ---
    "health": {
        "answer": (
            f"{E_SHIELD} <b>Axis Max Life Health & CI Riders</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Axis Max Life provides Critical Illness covers as riders\n"
            f"with main life insurance plans.\n\n"
            f"{E_CHECK} <b>Critical Illness Rider:</b>\n"
            f"  {E_PIN} Covers 40+ critical illnesses\n"
            f"  {E_PIN} Cancer, heart attack, stroke, kidney failure etc.\n"
            f"  {E_PIN} Lump-sum payout on diagnosis\n"
            f"  {E_PIN} Can be added with Term/Savings/ULIP plans\n"
            f"  {E_PIN} Premium: Rs 1-3 per lakh per day\n\n"
            f"{E_CHECK} <b>Hospital Cash Rider:</b>\n"
            f"  {E_PIN} Daily cash benefit during hospitalization\n"
            f"  {E_PIN} Rs 1,000-5,000/day\n\n"
            f"{E_BULB} <b>Selling Tips:</b>\n"
            f"  {E_PIN} 'Health insurance covers hospital bills, CI covers income loss'\n"
            f"  {E_PIN} 'Cancer treatment mein 6 months kaam nahi kar sakte - EMI kaun bharega?'\n"
            f"  {E_PIN} Always suggest CI rider with every term plan"
        ),
        "keywords": ["health", "critical illness", "cancer", "heart attack", "hospital", "medical", "rider", "ci rider", "critical"],
    },

    # --- COMMISSION ---
    "commission": {
        "answer": (
            f"{E_MONEY} <b>Commission Structure - Axis Max Life</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{E_CHECK} <b>First Year Commission:</b>\n"
            f"  {E_PIN} Term Plans: 15-20% of annual premium\n"
            f"  {E_PIN} Savings Plans: 25-35% of annual premium\n"
            f"  {E_PIN} ULIPs: 8-12% of annual premium\n"
            f"  {E_PIN} Single Premium: 2-3% of premium\n\n"
            f"{E_CHECK} <b>Renewal Commission:</b>\n"
            f"  {E_PIN} Term Plans: 5-7.5% (years 2-5)\n"
            f"  {E_PIN} Savings Plans: 5-7.5% (years 2-10)\n"
            f"  {E_PIN} ULIPs: 3-5% (years 2-5)\n\n"
            f"{E_CHART} <b>Income Building Tips:</b>\n"
            f"  {E_PIN} Policy persistency = renewal commission ka key\n"
            f"  {E_PIN} Cross-sell riders for extra commission\n"
            f"  {E_PIN} Focus on annual/quarterly mode (higher than monthly)\n"
            f"  {E_PIN} Top performer bonuses: Additional 5-15% on targets\n\n"
            f"{E_TROPHY} <b>Example Earnings:</b>\n"
            f"  10 term plans of Rs 50K premium = Rs 1 Lakh commission\n"
            f"  + Renewals = Rs 25K-37K per year for 4 more years\n\n"
            f"{E_FIRE} <b>Real income is in RENEWALS. Persistency is everything!</b>"
        ),
        "keywords": ["commission", "income", "earning", "payment", "payout", "paisa", "kitna milega", "kamai"],
    },

    # --- CLAIM PROCESS ---
    "claim": {
        "answer": (
            f"{E_MEMO} <b>Claim Process - Axis Max Life</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{E_STAR} <b>Axis Max Life Claim Settlement Ratio: 99.51%</b>\n"
            f"(Industry best - use this in every pitch!)\n\n"
            f"{E_CHECK} <b>Claim Steps:</b>\n"
            f"  1. Nominee/claimant calls 1860-120-5577\n"
            f"  2. Or visits www.axismaxlife.com > Claims\n"
            f"  3. Submit claim form + documents\n"
            f"  4. Company reviews within 30 days\n"
            f"  5. Payout via NEFT to nominee's bank\n\n"
            f"{E_PIN} <b>Required Documents:</b>\n"
            f"  {E_CHECK} Original policy document\n"
            f"  {E_CHECK} Death certificate (for death claim)\n"
            f"  {E_CHECK} FIR (if accidental death)\n"
            f"  {E_CHECK} Claimant's ID & address proof\n"
            f"  {E_CHECK} Cancelled cheque / bank details\n"
            f"  {E_CHECK} Medical records (last 3 months)\n\n"
            f"{E_BULB} <b>Agent's Role:</b>\n"
            f"  {E_PIN} Help nominee collect documents\n"
            f"  {E_PIN} Fill claim form correctly\n"
            f"  {E_PIN} Follow up with company\n"
            f"  {E_PIN} Your help builds lifelong trust = referrals!"
        ),
        "keywords": ["claim", "settlement", "death claim", "maturity claim", "nominee", "document", "claim ratio", "claim process"],
    },

    # --- TAX BENEFITS ---
    "tax": {
        "answer": (
            f"{E_MONEY} <b>Tax Benefits - Insurance Products</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{E_CHECK} <b>Section 80C - Premium Deduction:</b>\n"
            f"  {E_PIN} Up to Rs 1.5 Lakh/year deduction\n"
            f"  {E_PIN} Applies to: Term, Savings, ULIP, Child plans\n"
            f"  {E_PIN} Condition: Annual premium < 10% of sum assured\n\n"
            f"{E_CHECK} <b>Section 80CCC - Pension Plans:</b>\n"
            f"  {E_PIN} Additional Rs 50,000 deduction\n"
            f"  {E_PIN} Under Section 80CCD(1B) for NPS\n\n"
            f"{E_CHECK} <b>Section 10(10D) - Tax-Free Maturity:</b>\n"
            f"  {E_PIN} Maturity/death benefit completely TAX-FREE\n"
            f"  {E_PIN} Condition: Premium < 10% of sum assured\n"
            f"  {E_PIN} This is BIGGEST advantage over FD/MF!\n\n"
            f"{E_FIRE} <b>Selling Script:</b>\n"
            f"  'Rs 1.5 Lakh invest karo, Rs 46,800 tax bachao (30% slab).\n"
            f"  Matlab effective cost sirf Rs 1.03 Lakh. Plus maturity\n"
            f"  tax-free - FD mein yeh nahi milta!'"
        ),
        "keywords": ["tax", "80c", "80ccc", "10 10d", "tax benefit", "tax saving", "tax free", "deduction", "income tax"],
    },

    # --- WHOLE LIFE / SWAG ---
    "whole_life": {
        "answer": (
            f"{E_SHIELD} <b>Axis Max Life Whole Life Plans</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{E_STAR} <b>SWAG (Smart Wealth Assured Growth) Plan:</b>\n"
            f"  {E_PIN} Limited pay, whole life cover up to 99/100 years\n"
            f"  {E_PIN} Guaranteed maturity benefit + bonuses\n"
            f"  {E_PIN} Premium payment: 7/10/12 years only\n"
            f"  {E_PIN} Cover continues even after you stop paying\n"
            f"  {E_PIN} Loan facility available after 3 policy years\n"
            f"  {E_PIN} Min SA: Rs 5 Lakh\n\n"
            f"{E_CHECK} <b>Key USP:</b>\n"
            f"  {E_PIN} 'Pay for 10 years, stay covered for life!'\n"
            f"  {E_PIN} Guaranteed additions compound every year\n"
            f"  {E_PIN} Can be used as legacy/wealth transfer tool\n\n"
            f"{E_FIRE} <b>Best For:</b>\n"
            f"  {E_PIN} High net worth customers who want lifelong cover\n"
            f"  {E_PIN} Business owners wanting succession planning\n"
            f"  {E_PIN} Customers who want guaranteed + bonus returns"
        ),
        "keywords": ["swag", "whole life", "lifetime", "100 years", "smart wealth assured", "lifetime plan"],
    },

    # --- COMPARISON ---
    "comparison": {
        "answer": (
            f"{E_CHART} <b>Product Comparison Guide</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{E_STAR} <b>Term vs Savings vs ULIP:</b>\n\n"
            f"<b>Term Plan:</b>\n"
            f"  {E_PIN} Cheapest premium | Highest cover\n"
            f"  {E_PIN} No maturity benefit | Pure protection\n"
            f"  {E_PIN} Best for: Young earners with family\n\n"
            f"<b>Savings Plan:</b>\n"
            f"  {E_PIN} Moderate premium | Guaranteed returns\n"
            f"  {E_PIN} Maturity benefit + Life cover\n"
            f"  {E_PIN} Best for: Risk-averse customers\n\n"
            f"<b>ULIP:</b>\n"
            f"  {E_PIN} Premium goes to market | High return potential\n"
            f"  {E_PIN} 5 year lock-in | Market risk\n"
            f"  {E_PIN} Best for: Young, risk-taking investors\n\n"
            f"{E_BULB} <b>Agent Tip:</b> Every customer needs:\n"
            f"  1. FIRST: Term plan for base protection\n"
            f"  2. THEN: Savings/ULIP based on risk appetite\n"
            f"  3. ADD: Riders for comprehensive coverage"
        ),
        "keywords": ["compare", "comparison", "difference", "vs", "versus", "fark", "better", "which plan", "kaunsa"],
    },

    # --- SELLING TIPS ---
    "selling": {
        "answer": (
            f"{E_FIRE} <b>Top Selling Tips - Axis Max Life</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{E_TROPHY} <b>Top Performers ke Secrets:</b>\n\n"
            f"1. <b>Need-Based Selling:</b>\n"
            f"  {E_PIN} Pehle customer ki zaroorat samjho\n"
            f"  {E_PIN} Family situation, income, goals puchho\n"
            f"  {E_PIN} Phir product recommend karo\n\n"
            f"2. <b>Emotional Connect:</b>\n"
            f"  {E_PIN} 'Aap ki family ko Rs 50 lakh milega kya bina aapke?'\n"
            f"  {E_PIN} Story-telling use karo (real claim stories)\n\n"
            f"3. <b>Objection Handling:</b>\n"
            f"  {E_PIN} 'Abhi zaroorat nahi hai' -> 'Bimari hone ke baad insurance nahi milta'\n"
            f"  {E_PIN} 'Paise nahi hain' -> 'Rs 20/day = Rs 1 Cr cover'\n"
            f"  {E_PIN} 'Company trusted nahi' -> '99.51% claim ratio, Max Life is India #1'\n\n"
            f"4. <b>Follow-up Formula:</b>\n"
            f"  {E_PIN} 1st meeting: Listen + understand needs\n"
            f"  {E_PIN} 2nd meeting: Present solution + illustrations\n"
            f"  {E_PIN} 3rd meeting: Close the deal\n\n"
            f"{E_ROCKET} <b>Daily Target: 3 meetings = 1 policy/week = 4 policies/month</b>"
        ),
        "keywords": ["sell", "selling", "tips", "convince", "objection", "how to sell", "kaise bechein", "customer", "pitch"],
    },

    # --- PORTAL / TECH ISSUES ---
    "portal": {
        "answer": (
            f"{E_PHONE} <b>Portal & Technical Support</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{E_CHECK} <b>Agent Portal Login:</b>\n"
            f"  {E_PIN} URL: partner.axismaxlife.com\n"
            f"  {E_PIN} Login with Agent Code + Password\n"
            f"  {E_PIN} Forgot password: Click 'Reset Password' or call helpline\n\n"
            f"{E_CHECK} <b>Common Issues & Solutions:</b>\n"
            f"  {E_PIN} <b>Login not working:</b> Clear browser cache, try Chrome\n"
            f"  {E_PIN} <b>Policy not showing:</b> Wait 24-48 hours after issuance\n"
            f"  {E_PIN} <b>Commission not credited:</b> Check 15th of following month\n"
            f"  {E_PIN} <b>Proposal stuck:</b> Check for pending documents/medicals\n\n"
            f"{E_PHONE} <b>Helpline Numbers:</b>\n"
            f"  {E_PIN} Agent Helpdesk: 1860-120-5577\n"
            f"  {E_PIN} IT Support: 022-71965577\n"
            f"  {E_PIN} Working hours: Mon-Sat 9 AM - 8 PM\n\n"
            f"{E_BULB} <b>ADM Tip:</b> Most portal issues are browser/cache related.\n"
            f"  Guide agents to use Chrome in incognito mode first."
        ),
        "keywords": ["portal", "login", "password", "website", "technical", "system", "error", "IT", "not working", "kaam nahi", "helpline", "helpdesk"],
    },

    # --- AXIS MAX LIFE COMPANY INFO ---
    "company": {
        "answer": (
            f"{E_SHIELD} <b>About Axis Max Life Insurance</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{E_STAR} <b>Key Facts (use in every pitch!):</b>\n"
            f"  {E_CHECK} Joint venture: Axis Bank + Max Financial\n"
            f"  {E_CHECK} 20+ years in India\n"
            f"  {E_CHECK} 1 Crore+ customers served\n"
            f"  {E_CHECK} 1 Lakh+ advisor network\n"
            f"  {E_CHECK} Claim Settlement Ratio: <b>99.51%</b>\n"
            f"  {E_CHECK} Rated #1 in private life insurance service\n"
            f"  {E_CHECK} Available across 300+ cities\n"
            f"  {E_CHECK} Backed by Axis Bank (India's 3rd largest private bank)\n\n"
            f"{E_TROPHY} <b>Awards & Recognition:</b>\n"
            f"  {E_PIN} Great Place to Work certified\n"
            f"  {E_PIN} National award for claims service\n"
            f"  {E_PIN} Digital innovation leader\n\n"
            f"{E_FIRE} <b>Trust Pitch:</b>\n"
            f"  'Axis Bank ka naam suna hai? Unki insurance company hai.\n"
            f"  99.51% claims pay karte hain. India mein sabse reliable.'"
        ),
        "keywords": ["axis max life", "company", "about", "who", "history", "rating", "review", "trust", "reliable", "company profile"],
    },

    # --- GROUP INSURANCE ---
    "group": {
        "answer": (
            f"{E_PERSON} <b>Axis Max Life Group Insurance</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"SME / Corporate clients ke liye.\n\n"
            f"{E_CHECK} <b>Group Term Life:</b>\n"
            f"  {E_PIN} Employer pays premium for all employees\n"
            f"  {E_PIN} Flat or graded cover based on salary\n"
            f"  {E_PIN} Minimum 10 lives to start\n"
            f"  {E_PIN} Competitive pricing for groups\n\n"
            f"{E_CHECK} <b>Group Credit Life:</b>\n"
            f"  {E_PIN} Covers loan outstanding on borrower's death\n"
            f"  {E_PIN} Banks/NBFCs ke liye\n"
            f"  {E_PIN} Decreasing cover aligned with loan tenure\n\n"
            f"{E_BULB} <b>Lead Generation Tip:</b>\n"
            f"  Target local businesses with 10+ employees.\n"
            f"  Offer free quote comparison with their current provider."
        ),
        "keywords": ["group", "corporate", "employer", "employee", "company insurance", "business", "sme"],
    },

    # --- RENEWAL / PERSISTENCY ---
    "renewal": {
        "answer": (
            f"{E_CALENDAR} <b>Policy Renewal & Persistency</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{E_WARNING} <b>Why Persistency Matters:</b>\n"
            f"  {E_PIN} Your renewal commission depends on it!\n"
            f"  {E_PIN} Company tracks 13th month persistency\n"
            f"  {E_PIN} Low persistency = lower commission slabs\n"
            f"  {E_PIN} High persistency = bonus + rewards\n\n"
            f"{E_CHECK} <b>How to Improve Persistency:</b>\n"
            f"  {E_PIN} Set premium reminder 7 days before due date\n"
            f"  {E_PIN} Help customers set up ECS/auto-debit\n"
            f"  {E_PIN} Call customers on premium due date\n"
            f"  {E_PIN} Annual policy review - show value added\n"
            f"  {E_PIN} Address lapse concerns immediately\n\n"
            f"{E_CHECK} <b>Grace Period:</b>\n"
            f"  {E_PIN} Monthly mode: 15 days grace\n"
            f"  {E_PIN} Quarterly/Half-yearly/Annual: 30 days grace\n"
            f"  {E_PIN} After grace period: Policy lapses!\n\n"
            f"{E_FIRE} <b>Revival:</b> Lapsed policy can be revived within 2-5 years\n"
            f"  with back premiums + interest + medical (if needed)."
        ),
        "keywords": ["renewal", "renew", "persistency", "lapse", "revival", "revive", "due date", "grace period", "premium due"],
    },

    # --- PREMIUM CALCULATION ---
    "premium": {
        "answer": (
            f"{E_MONEY} <b>Premium Calculation Guide</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{E_CHECK} <b>Factors Affecting Premium:</b>\n"
            f"  {E_PIN} Age (younger = cheaper)\n"
            f"  {E_PIN} Sum Assured (higher cover = higher premium)\n"
            f"  {E_PIN} Smoking status (non-smoker gets 30-40% discount)\n"
            f"  {E_PIN} Health condition (medical tests for higher SA)\n"
            f"  {E_PIN} Policy term (longer = slightly higher)\n"
            f"  {E_PIN} Payment mode (annual is cheapest)\n\n"
            f"{E_STAR} <b>Quick Premium Examples (Term Plan):</b>\n"
            f"  25 yr male, non-smoker, Rs 1 Cr:\n"
            f"    {E_PIN} ~Rs 595/month or ~Rs 7,000/year\n\n"
            f"  35 yr male, non-smoker, Rs 1 Cr:\n"
            f"    {E_PIN} ~Rs 1,200/month or ~Rs 13,500/year\n\n"
            f"  30 yr female, non-smoker, Rs 50 Lakh:\n"
            f"    {E_PIN} ~Rs 400/month or ~Rs 4,500/year\n\n"
            f"{E_BULB} <b>Tip:</b> Always show annual premium + per-day cost\n"
            f"  'Sirf Rs 20/day mein Rs 1 Crore ka cover!'"
        ),
        "keywords": ["premium", "price", "cost", "kitna", "quote", "calculate", "kitne ka", "rate"],
    },

    # --- LIC COMPARISON ---
    "lic_compare": {
        "answer": (
            f"{E_CHART} <b>Axis Max Life vs LIC Comparison</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Customer says 'LIC already hai' - here's your response:\n\n"
            f"{E_CHECK} <b>Axis Max Life Advantages:</b>\n"
            f"  {E_PIN} Online purchasing - no paperwork hassle\n"
            f"  {E_PIN} Lower premiums for same coverage\n"
            f"  {E_PIN} Claim ratio: 99.51% vs LIC's 98.6%\n"
            f"  {E_PIN} Faster claim settlement (30 days)\n"
            f"  {E_PIN} Better digital experience & app\n"
            f"  {E_PIN} Backed by Axis Bank\n\n"
            f"{E_BULB} <b>Handling the Objection:</b>\n"
            f"  {E_PIN} 'LIC achhi hai, but Axis Max Life sasti hai same cover ke liye'\n"
            f"  {E_PIN} 'Ek policy kaafi nahi - diversify like investments'\n"
            f"  {E_PIN} 'LIC ke paas traditional plans hain, humara term plan 40% sasta hai'\n"
            f"  {E_PIN} 'Axis Bank ki backing hai - trust guaranteed'\n\n"
            f"{E_FIRE} <b>Never badmouth LIC!</b>\n"
            f"  Always position as 'additional protection', not replacement."
        ),
        "keywords": ["lic", "compare lic", "lic better", "lic vs", "competition", "competitor", "other company", "hdfc life", "icici", "sbi life"],
    },
}


def _get_local_answer(question: str) -> dict:
    """Match question keywords to provide an answer from the local product knowledge base."""
    question_lower = question.lower()

    # Check each product knowledge entry for keyword matches
    best_match = None
    best_score = 0

    for key, data in PRODUCT_KNOWLEDGE.items():
        score = 0
        for kw in data["keywords"]:
            if kw in question_lower:
                # Longer keyword matches score higher
                score += len(kw)

        if score > best_score:
            best_score = score
            best_match = key

    if best_match and best_score > 0:
        return {"answer": PRODUCT_KNOWLEDGE[best_match]["answer"]}

    # Smart default - give a helpful menu instead of saying "demo mode"
    return {
        "answer": (
            f"{E_BRAIN} <b>Axis Max Life - Product Expert</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{E_SPARKLE} Great question!\n\n"
            f"Your question: <i>'{question}'</i>\n\n"
            f"Main aapko in topics pe detailed info de sakta hoon.\n"
            f"Specific topic type karein ya tap karein:\n\n"
            f"  {E_SHIELD} <b>Term Plans</b> - type 'term plan'\n"
            f"  {E_CHART} <b>ULIPs</b> - type 'ulip'\n"
            f"  {E_MONEY} <b>Savings Plans</b> - type 'savings plan'\n"
            f"  {E_STAR} <b>Child Plans</b> - type 'child plan'\n"
            f"  {E_CALENDAR} <b>Retirement</b> - type 'pension'\n"
            f"  {E_SHIELD} <b>Health/CI Riders</b> - type 'health rider'\n"
            f"  {E_MONEY} <b>Commission Info</b> - type 'commission'\n"
            f"  {E_MEMO} <b>Claim Process</b> - type 'claim process'\n"
            f"  {E_MONEY} <b>Tax Benefits</b> - type 'tax benefit'\n"
            f"  {E_FIRE} <b>Selling Tips</b> - type 'selling tips'\n"
            f"  {E_PHONE} <b>Portal Help</b> - type 'portal issue'\n"
            f"  {E_CHART} <b>Product Comparison</b> - type 'compare plans'\n"
            f"  {E_MONEY} <b>Premium Calculator</b> - type 'premium'\n"
            f"  {E_CHART} <b>LIC Comparison</b> - type 'lic compare'\n\n"
            f"{E_BULB} Try asking a specific question for detailed info!"
        ),
    }


# ---------------------------------------------------------------------------
# Ask another keyboard
# ---------------------------------------------------------------------------

def _ask_another_keyboard() -> InlineKeyboardMarkup:
    """Keyboard with 'Ask Another' and 'Done' buttons."""
    buttons = [
        [InlineKeyboardButton(f"{E_BRAIN} Ask Another / Aur Puchho", callback_data="ask_another")],
        [
            InlineKeyboardButton(f"{E_BOOK} Training", callback_data="ask_train"),
            InlineKeyboardButton(f"{E_CHECK} Done", callback_data="ask_done"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def _quick_topics_keyboard() -> InlineKeyboardMarkup:
    """Keyboard with popular topic shortcuts."""
    buttons = [
        [
            InlineKeyboardButton(f"{E_SHIELD} Term Plans", callback_data="ask_topic_term"),
            InlineKeyboardButton(f"{E_CHART} ULIPs", callback_data="ask_topic_ulip"),
        ],
        [
            InlineKeyboardButton(f"{E_MONEY} Savings", callback_data="ask_topic_savings"),
            InlineKeyboardButton(f"{E_STAR} Child Plans", callback_data="ask_topic_child"),
        ],
        [
            InlineKeyboardButton(f"{E_MONEY} Commission", callback_data="ask_topic_commission"),
            InlineKeyboardButton(f"{E_MEMO} Claims", callback_data="ask_topic_claim"),
        ],
        [
            InlineKeyboardButton(f"{E_FIRE} Selling Tips", callback_data="ask_topic_selling"),
            InlineKeyboardButton(f"{E_MONEY} Tax Benefits", callback_data="ask_topic_tax"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------------------------------
# Entry: /ask
# ---------------------------------------------------------------------------

async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the product Q&A flow."""
    logger.info(">>> /ask command from user %s", update.effective_user.id)

    # Check for inline question: /ask What is term insurance?
    if context.args:
        question = " ".join(context.args)
        return await _process_question(update, context, question)

    await update.message.reply_text(
        f"{E_BRAIN} <b>AI Product Q&A / AI Se Puchho</b>\n\n"
        f"{E_SPARKLE} Ask me anything about Axis Max Life products!\n"
        f"Bima products ke baare mein kuch bhi puchho!\n\n"
        f"{E_BULB} <b>Example questions:</b>\n"
        f"  {E_PIN} 'Term plan kya hai?'\n"
        f"  {E_PIN} 'ULIP vs savings plan?'\n"
        f"  {E_PIN} 'Commission kitna milta hai?'\n"
        f"  {E_PIN} 'Claim process kaise kaam karta hai?'\n"
        f"  {E_PIN} 'Customer ko kaise convince karein?'\n\n"
        f"{E_PENCIL} <b>Type your question below or tap a topic:</b>",
        parse_mode="HTML",
        reply_markup=_quick_topics_keyboard(),
    )
    return AskStates.WAITING_QUESTION


# ---------------------------------------------------------------------------
# Process question
# ---------------------------------------------------------------------------

async def receive_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and process a product question."""
    question = update.message.text.strip()
    logger.info(">>> Ask question from %s: %s", update.effective_user.id, question)

    if len(question) < 2:
        await update.message.reply_text(
            f"{E_WARNING} Please ask a more detailed question.\n"
            f"Thoda aur detail mein puchho.\n\n"
            f"{E_PENCIL} Type your question:",
            parse_mode="HTML",
        )
        return AskStates.WAITING_QUESTION

    return await _process_question(update, context, question)


async def _process_question(update: Update, context: ContextTypes.DEFAULT_TYPE, question: str) -> int:
    """Process a question and return AI answer."""
    telegram_id = update.effective_user.id

    # Show thinking message
    msg = update.message or (update.callback_query.message if update.callback_query else None)
    thinking_msg = None
    if msg:
        try:
            thinking_msg = await msg.reply_text(
                f"{E_BRAIN} <b>Sochne do...</b> {E_SPARKLE}",
                parse_mode="HTML",
            )
        except Exception:
            pass

    # Try AI-powered API first
    try:
        answer_resp = await api_client.ask_product_question(telegram_id, question)
    except Exception:
        answer_resp = None

    if answer_resp and not answer_resp.get("error") and answer_resp.get("answer"):
        answer_data = answer_resp
    else:
        # AI API unavailable — use local product knowledge base
        logger.info("AI API unavailable, using local knowledge base for question: %s", question[:50])
        answer_data = _get_local_answer(question)

    # Get the answer text
    answer_text = answer_data.get("answer", "")
    if not answer_text:
        answer_text = format_product_answer(answer_data)

    # Build response with the question shown
    response_text = (
        f"{E_CHAT} <b>Q:</b> <i>{question}</i>\n\n"
        f"{answer_text}"
    )

    # Delete thinking message
    if thinking_msg:
        try:
            await thinking_msg.delete()
        except Exception:
            pass

    # Send answer
    if msg:
        sent_msg = await msg.reply_text(
            response_text,
            parse_mode="HTML",
            reply_markup=_ask_another_keyboard(),
        )
        await send_voice_response(sent_msg, response_text)

    return AskStates.WAITING_QUESTION


# ---------------------------------------------------------------------------
# Callback actions
# ---------------------------------------------------------------------------

async def ask_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle ask flow callback buttons."""
    query = update.callback_query
    await query.answer()

    data = query.data

    # Quick topic buttons
    if data.startswith("ask_topic_"):
        topic = data.replace("ask_topic_", "")
        if topic in PRODUCT_KNOWLEDGE:
            answer_text = PRODUCT_KNOWLEDGE[topic]["answer"]
            topic_name = topic.replace("_", " ").title()
            topic_response = (
                f"{E_CHAT} <b>Q:</b> <i>Tell me about {topic_name}</i>\n\n"
                f"{answer_text}"
            )
            await query.edit_message_text(
                topic_response,
                parse_mode="HTML",
                reply_markup=_ask_another_keyboard(),
            )
            await send_voice_response(query.message, topic_response)
        return AskStates.WAITING_QUESTION

    if data == "ask_another":
        await query.edit_message_text(
            f"{E_BRAIN} <b>Ask Another Question / Aur Puchho</b>\n\n"
            f"{E_PENCIL} Type your question below or tap a topic:",
            parse_mode="HTML",
            reply_markup=_quick_topics_keyboard(),
        )
        return AskStates.WAITING_QUESTION

    if data == "ask_train":
        await query.edit_message_text(
            f"{E_BOOK} Use /train to start product training!\n"
            f"Training ke liye /train type karein.",
            parse_mode="HTML",
        )
        return ConversationHandler.END

    # ask_done
    await query.edit_message_text(
        f"{E_CHECK} <b>Q&A session complete!</b>\n\n"
        f"Bahut achha! {E_SPARKLE} Aapne achhe sawal puchhe!\n\n"
        f"{E_BULB} Kabhi bhi /ask use karke sawal puch sakte hain.\n"
        f"{E_FIRE} Knowledge is power - keep learning!",
        parse_mode="HTML",
    )
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

async def cancel_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel ask flow."""
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(cancelled(), parse_mode="HTML")
    else:
        await update.message.reply_text(cancelled(), parse_mode="HTML")

    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Build ConversationHandler
# ---------------------------------------------------------------------------

def build_ask_handler() -> ConversationHandler:
    """Build the /ask conversation handler."""
    return ConversationHandler(
        entry_points=[CommandHandler("ask", ask_command)],
        states={
            AskStates.WAITING_QUESTION: [
                CallbackQueryHandler(ask_callback, pattern=r"^ask_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_question),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_ask),
            CallbackQueryHandler(cancel_ask, pattern=r"^cancel$"),
        ],
        name="ask_ai",
        persistent=True,
    )
