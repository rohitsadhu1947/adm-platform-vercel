"""
Training module endpoints.
Provides training modules, quiz submission, progress tracking, and leaderboard.
"""

import random
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import TrainingProgress, ADM
from schemas import (
    TrainingModuleInfo,
    QuizAnswer,
    TrainingProgressResponse,
    LeaderboardEntry,
)

router = APIRouter(prefix="/training", tags=["Training"])

# ---------------------------------------------------------------------------
# In-memory training module definitions with quiz questions & learning material
# ---------------------------------------------------------------------------
TRAINING_MODULES = [
    {
        "module_name": "Term Insurance Masterclass",
        "module_category": "product_knowledge",
        "description": "Comprehensive training on Max Life Smart Secure Plus, Online Term Plan Plus, and Smart Fixed-Return Digital Plan. Learn features, USPs, target audience, common objections, and competitive positioning.",
        "learning_material": {
            "sections": [
                {
                    "title": "What is Term Insurance?",
                    "content": "Term insurance is the purest and most affordable form of life insurance. It provides a death benefit (sum assured) to the nominee if the policyholder passes away during the policy term. Unlike endowment or ULIP plans, term insurance does not have a savings or investment component — the entire premium goes towards risk coverage, making it significantly cheaper.",
                },
                {
                    "title": "Products Covered in This Module",
                    "content": "This module covers three key Axis Max Life term insurance products that every ADM and agent must know thoroughly.",
                    "bullets": [
                        "Smart Secure Plus Plan — flagship offline term plan with sum assured up to Rs 10 crore",
                        "Online Term Plan Plus — digital-first plan with whole life cover option up to age 85",
                        "Smart Fixed-Return Digital Plan — term plan with return of premium benefit",
                    ],
                },
                {
                    "title": "Smart Secure Plus — Key Features",
                    "key_points": [
                        {"label": "Sum Assured Range", "value": "Rs 25 lakh to Rs 10 crore"},
                        {"label": "Policy Term", "value": "10 to 40 years (minimum 10 years)"},
                        {"label": "Premium Payment Options", "value": "Regular Pay, Limited Pay (5/10/15 years) — NO Single Premium"},
                        {"label": "Entry Age", "value": "18 to 65 years"},
                        {"label": "Tax Benefits", "value": "Premiums under Section 80C, death benefit under Section 10(10D)"},
                        {"label": "Riders Available", "value": "Accidental Death, Critical Illness, Waiver of Premium"},
                    ],
                },
                {
                    "title": "Online Term Plan Plus — Differentiators",
                    "content": "The Online Term Plan Plus is designed for digitally savvy customers who prefer buying insurance online. Its key USP vs Smart Secure Plus is the whole life cover option that extends coverage up to age 85, compared to the standard term structure.",
                    "bullets": [
                        "Available only through online channel — no paperwork",
                        "Whole life cover option up to age 85 (unique differentiator)",
                        "Lower premiums than offline plans due to reduced distribution costs",
                        "Instant policy issuance for eligible cases",
                    ],
                },
                {
                    "title": "Customer Objection Handling",
                    "content": "Common objections and how to address them:",
                    "bullets": [
                        "'I don't get anything back if I survive' — Explain that term insurance is like car/home insurance; the low cost means massive coverage. Rs 500/month can give Rs 1 crore cover.",
                        "'I already have insurance from my employer' — Employer cover ends when you leave. It's usually only 3-5x salary. Personal term cover stays with you for life.",
                        "'I'm young and healthy, I don't need it' — This is exactly when premiums are lowest. A 25-year-old pays 40% less than a 35-year-old for the same cover.",
                    ],
                },
            ],
            "do_and_dont": {
                "do": [
                    "Always calculate the customer's Human Life Value before recommending sum assured",
                    "Highlight the claim settlement ratio (~99.51%) to build trust",
                    "Explain the tax benefits clearly — Section 80C for premiums, 10(10D) for death benefit",
                    "Recommend riders based on customer profile (Critical Illness for 35+ customers)",
                ],
                "dont": [
                    "Never compare term insurance unfavorably with endowment plans to push higher-commission products",
                    "Don't promise returns — term insurance is pure protection",
                    "Never recommend Single Premium for Smart Secure Plus (it's not available)",
                    "Don't skip the nominee and beneficiary discussion",
                ],
            },
            "target_audience": "Salaried professionals aged 25-45 with dependents, new parents, home loan holders needing collateral cover",
            "estimated_reading_time": "8 minutes",
        },
        "questions": {
            "q1": {
                "question": "What is the maximum sum assured available under Max Life Smart Secure Plus Plan?",
                "options": ["Rs 5 crore", "Rs 10 crore", "Rs 15 crore", "Rs 20 crore"],
                "correct": "Rs 10 crore",
            },
            "q2": {
                "question": "Which tax section provides benefits on term insurance premiums?",
                "options": ["Section 80D", "Section 80C", "Section 10(23D)", "Section 54"],
                "correct": "Section 80C",
            },
            "q3": {
                "question": "What is the minimum policy term for Smart Secure Plus Plan?",
                "options": ["5 years", "10 years", "15 years", "20 years"],
                "correct": "10 years",
            },
            "q4": {
                "question": "Which of the following is NOT a premium payment option for Smart Secure Plus?",
                "options": ["Regular Pay", "Limited Pay - 5 years", "Single Premium", "Limited Pay - 15 years"],
                "correct": "Single Premium",
            },
            "q5": {
                "question": "What additional benefit does the Online Term Plan Plus offer compared to Smart Secure Plus?",
                "options": ["Maturity benefit", "Whole life cover option up to age 85", "Investment returns", "Loan facility"],
                "correct": "Whole life cover option up to age 85",
            },
        },
    },
    {
        "module_name": "ULIP Fund Selection Guide",
        "module_category": "product_knowledge",
        "description": "Deep dive into Max Life ULIPs - Online Savings Plan, Platinum Wealth Plan, and Fast Track Super Plan. Understand fund options, NAV concepts, switching, and wealth boosters.",
        "learning_material": {
            "sections": [
                {
                    "title": "Understanding ULIPs",
                    "content": "Unit Linked Insurance Plans (ULIPs) combine life insurance with market-linked investment. A portion of the premium covers life risk, while the remainder is invested in equity, debt, or balanced funds chosen by the policyholder. ULIPs are regulated by IRDAI with a mandatory 5-year lock-in period.",
                },
                {
                    "title": "Axis Max Life ULIP Products",
                    "bullets": [
                        "Online Savings Plan — entry-level ULIP with 4 fund options, 12 free switches/year, ideal for first-time investors",
                        "Platinum Wealth Plan — premium ULIP (min Rs 2.5 lakh/year) with wealth boosters starting Year 6, designed for HNI clients",
                        "Fast Track Super Plan — aggressive growth ULIP for long-term wealth creation with multiple fund strategies",
                    ],
                },
                {
                    "title": "Key ULIP Concepts Every Agent Must Know",
                    "key_points": [
                        {"label": "NAV (Net Asset Value)", "value": "Price per unit of a fund — changes daily based on market performance"},
                        {"label": "Lock-in Period", "value": "5 years as mandated by IRDAI — no partial withdrawal before this"},
                        {"label": "Fund Switching", "value": "Moving money between fund options (equity to debt or vice versa) based on market outlook"},
                        {"label": "Mortality Charges", "value": "Cost of life cover deducted monthly from the fund value"},
                        {"label": "Wealth Boosters", "value": "Extra units added to the fund as a loyalty benefit (Platinum Wealth: from Year 6)"},
                        {"label": "Top-up Premium", "value": "Additional investment over and above the regular premium"},
                    ],
                },
                {
                    "title": "When to Recommend ULIPs vs Mutual Funds",
                    "content": "ULIPs combine insurance + investment with tax benefits under Section 80C (premiums) and 10(10D) (maturity proceeds if conditions met). Unlike mutual funds, ULIPs offer life cover, disciplined long-term investing via lock-in, and free fund switching without capital gains tax during the policy term.",
                },
            ],
            "do_and_dont": {
                "do": [
                    "Explain the lock-in period clearly — 5 years minimum",
                    "Show historical fund performance data when pitching",
                    "Match fund selection to customer's risk appetite and time horizon",
                    "Highlight free switching as a market volatility management tool",
                ],
                "dont": [
                    "Never guarantee returns — ULIPs are market-linked",
                    "Don't recommend ULIPs for short-term goals (< 7 years)",
                    "Never hide the mortality charges or fund management fees",
                    "Don't compare ULIP returns with fixed deposits directly",
                ],
            },
            "target_audience": "Investors aged 28-50 with medium to high risk appetite, looking for tax-efficient long-term wealth creation with life cover",
            "estimated_reading_time": "10 minutes",
        },
        "questions": {
            "q1": {
                "question": "How many fund options does Max Life Online Savings Plan offer?",
                "options": ["2", "4", "7", "11"],
                "correct": "4",
            },
            "q2": {
                "question": "What is the minimum annual premium for Platinum Wealth Plan?",
                "options": ["Rs 50,000", "Rs 1 lakh", "Rs 2.5 lakh", "Rs 5 lakh"],
                "correct": "Rs 2.5 lakh",
            },
            "q3": {
                "question": "After how many years does ULIP lock-in period end as per IRDAI?",
                "options": ["3 years", "5 years", "7 years", "10 years"],
                "correct": "5 years",
            },
            "q4": {
                "question": "How many free fund switches per year are allowed in Online Savings Plan?",
                "options": ["4", "8", "12", "Unlimited"],
                "correct": "12",
            },
            "q5": {
                "question": "From which year do wealth boosters start in Platinum Wealth Plan?",
                "options": ["Year 1", "Year 3", "Year 6", "Year 10"],
                "correct": "Year 6",
            },
        },
    },
    {
        "module_name": "Savings Plans Deep Dive",
        "module_category": "product_knowledge",
        "description": "Master the savings product portfolio - Smart Wealth Plan, Guaranteed Smart Income Plan, and Smart Secure Savings Plan. Learn guaranteed additions, income periods, and loan facilities.",
        "learning_material": {
            "sections": [
                {
                    "title": "Why Savings Plans?",
                    "content": "Savings plans are ideal for customers who want guaranteed returns with life cover. Unlike ULIPs, savings plans are not market-linked — they provide guaranteed additions, bonuses, and income streams. These are the bread-and-butter products for Indian middle-class families who prioritize capital safety.",
                },
                {
                    "title": "Product Portfolio",
                    "key_points": [
                        {"label": "Smart Wealth Plan", "value": "Guaranteed additions from Year 1, loyalty additions from Year 11, multiple payout options"},
                        {"label": "Guaranteed Smart Income Plan", "value": "Income period up to 40 years, joint life option (unique in market), guaranteed regular income"},
                        {"label": "Smart Secure Savings Plan", "value": "Loan facility available after 3 years, flexible premium payment, guaranteed maturity benefit"},
                    ],
                },
                {
                    "title": "Selling Points for Each Customer Segment",
                    "bullets": [
                        "For salaried professionals: Smart Wealth Plan — disciplined savings with guaranteed growth, tax benefits",
                        "For retirees/near-retirees: Guaranteed Smart Income Plan — lifelong income stream up to 40 years, joint life for spouse protection",
                        "For self-employed: Smart Secure Savings Plan — loan facility after 3 years provides emergency liquidity",
                        "For women customers: Joint life option in Guaranteed Smart Income Plan — covers both spouses",
                    ],
                },
            ],
            "do_and_dont": {
                "do": [
                    "Use the guaranteed additions and loyalty additions as key differentiators",
                    "Show the power of compounding with Year 1 guaranteed additions",
                    "Highlight the joint life option for couples",
                    "Mention the loan facility for liquidity-conscious customers",
                ],
                "dont": [
                    "Don't compare savings plan returns with equity market returns",
                    "Never hide the premium payment commitment period",
                    "Don't forget to explain the surrender value implications",
                    "Never suggest policy loans as a regular income source",
                ],
            },
            "target_audience": "Conservative investors aged 30-55, families planning for milestones, couples wanting joint life coverage",
            "estimated_reading_time": "7 minutes",
        },
        "questions": {
            "q1": {
                "question": "From which year do guaranteed additions start in Smart Wealth Plan?",
                "options": ["Year 1", "Year 3", "Year 5", "Year 7"],
                "correct": "Year 1",
            },
            "q2": {
                "question": "What is the maximum income period available in Guaranteed Smart Income Plan?",
                "options": ["20 years", "25 years", "30 years", "40 years"],
                "correct": "40 years",
            },
            "q3": {
                "question": "After how many years is loan facility available in Smart Secure Savings Plan?",
                "options": ["1 year", "2 years", "3 years", "5 years"],
                "correct": "3 years",
            },
            "q4": {
                "question": "What unique feature does Guaranteed Smart Income Plan offer?",
                "options": ["Market-linked returns", "Joint life option", "Zero premium allocation", "Daily NAV updates"],
                "correct": "Joint life option",
            },
            "q5": {
                "question": "When do loyalty additions start in Smart Wealth Plan?",
                "options": ["Year 5", "Year 7", "Year 11", "Year 15"],
                "correct": "Year 11",
            },
        },
    },
    {
        "module_name": "Child Plan Selling Strategies",
        "module_category": "product_knowledge",
        "description": "Learn to position and sell Shiksha Plus Super Plan and Super Investment Plan. Understand payout milestones, premium waiver benefits, and emotional selling techniques.",
        "learning_material": {
            "sections": [
                {
                    "title": "The Emotional Appeal of Child Plans",
                    "content": "Child plans are among the easiest insurance products to sell because they tap into every parent's deepest aspiration — securing their child's future. The key is to connect the product to specific life milestones: college admission at 18, professional education at 21, and wedding/startup capital at 24.",
                },
                {
                    "title": "Product Features",
                    "key_points": [
                        {"label": "Shiksha Plus Super Plan", "value": "Guaranteed payouts at child's age 18, 21, and 24 — aligned with education and career milestones"},
                        {"label": "Super Investment Plan", "value": "ULIP-based child plan for market-linked growth with premium waiver benefit"},
                        {"label": "Premium Waiver", "value": "If parent (policyholder) passes away, all future premiums are waived but the fund/policy continues for the child"},
                        {"label": "Flexibility", "value": "Super Investment Plan offers fund switching to adjust risk as the child grows older"},
                    ],
                },
                {
                    "title": "Selling Techniques",
                    "bullets": [
                        "Start with the child's age and work backward — 'Your daughter is 5, so in 13 years she'll need college funds'",
                        "Use milestone-based framing: 'Rs X at 18 for college, Rs Y at 21 for MBA, Rs Z at 24 for her startup'",
                        "The premium waiver is the most powerful feature — 'Even if something happens to you, your child's education fund continues'",
                        "For ULIP-savvy parents, position Super Investment Plan as growth + protection",
                    ],
                },
            ],
            "do_and_dont": {
                "do": [
                    "Always lead with the child's dreams and milestones",
                    "Emphasize the premium waiver benefit heavily — it's the emotional clincher",
                    "Calculate exact corpus needed at each milestone based on inflation",
                    "Show how starting early reduces the monthly premium significantly",
                ],
                "dont": [
                    "Don't use fear-based selling ('What if you die?') — use aspiration-based selling instead",
                    "Never ignore the spouse in the conversation — both parents make this decision",
                    "Don't recommend Super Investment Plan (ULIP) for goals less than 10 years away",
                    "Never under-estimate the corpus needed — account for education inflation at 10-12% per year",
                ],
            },
            "target_audience": "Parents aged 25-40 with children under 10, grandparents, expecting couples",
            "estimated_reading_time": "6 minutes",
        },
        "questions": {
            "q1": {
                "question": "At what ages does Shiksha Plus Super Plan provide guaranteed payouts?",
                "options": ["16, 18, 21", "18, 21, 24", "18, 21, 25", "21, 24, 28"],
                "correct": "18, 21, 24",
            },
            "q2": {
                "question": "What happens to the child plan if the parent passes away?",
                "options": ["Plan terminates", "Premiums are waived and fund continues", "Child must pay premiums", "Sum assured is paid and plan ends"],
                "correct": "Premiums are waived and fund continues",
            },
            "q3": {
                "question": "Which type of plan is Super Investment Plan?",
                "options": ["Endowment", "ULIP", "Term", "Annuity"],
                "correct": "ULIP",
            },
        },
    },
    {
        "module_name": "Pension Products Workshop",
        "module_category": "product_knowledge",
        "description": "Retirement planning with Guaranteed Lifetime Income Plan and Forever Young Pension Plan. Cover annuity options, commutation rules, and tax benefits under 80CCC.",
        "learning_material": {
            "sections": [
                {
                    "title": "The Retirement Gap in India",
                    "content": "Less than 10% of India's workforce has adequate retirement savings. With increasing life expectancy (average 72 years) and nuclear families, retirement planning is no longer optional. Pension products provide guaranteed income for life, addressing the biggest fear of retirees — outliving their savings.",
                },
                {
                    "title": "Product Comparison",
                    "key_points": [
                        {"label": "Guaranteed Lifetime Income Plan", "value": "Lifelong guaranteed pension, multiple annuity options, vesting at age 45-80"},
                        {"label": "Forever Young Pension Plan", "value": "Flexible accumulation phase, deferred annuity, bonus additions during accumulation"},
                        {"label": "Commutation", "value": "Up to 1/3rd of the corpus can be taken as lump sum at retirement; rest converts to pension"},
                        {"label": "Tax Benefits", "value": "Premiums under Section 80CCC (within 80C limit), 1/3rd commutation tax-free, pension taxable as income"},
                    ],
                },
                {
                    "title": "How to Position Pension Plans",
                    "bullets": [
                        "For customers aged 35-45: 'You have 20 years to build a pension corpus — starting now means lower premiums and higher accumulation'",
                        "For customers aged 50+: 'Guaranteed Lifetime Income Plan — no market risk, pension starts immediately on vesting'",
                        "Address the 'I have PPF/NPS' objection: 'Those give a corpus; this gives guaranteed lifetime income — you'll never run out'",
                        "Use the spouse angle: 'Joint life annuity ensures your spouse continues to receive pension if something happens to you'",
                    ],
                },
            ],
            "do_and_dont": {
                "do": [
                    "Calculate the customer's retirement gap (current savings vs needed corpus)",
                    "Explain the difference between accumulation and distribution phases clearly",
                    "Highlight that pension is guaranteed for life — unlike SWPs from mutual funds",
                    "Show the tax advantage of Section 80CCC deduction",
                ],
                "dont": [
                    "Don't confuse pension plans with endowment plans in your pitch",
                    "Never ignore the annuity taxation — pension income is taxable",
                    "Don't recommend pension plans for customers with less than 10 years to retirement without explaining limited accumulation",
                    "Never suggest that 1/3rd commutation is 'free money' — explain its impact on pension amount",
                ],
            },
            "target_audience": "Professionals aged 35-55 planning retirement, self-employed without employer pension, NRI returnees",
            "estimated_reading_time": "7 minutes",
        },
        "questions": {
            "q1": {
                "question": "What fraction of the pension corpus can be commuted (lump sum) at retirement?",
                "options": ["1/4th", "1/3rd", "1/2", "Full amount"],
                "correct": "1/3rd",
            },
            "q2": {
                "question": "Under which tax section do pension plan premiums qualify for deduction?",
                "options": ["Section 80C", "Section 80CCC", "Section 80D", "Section 80E"],
                "correct": "Section 80CCC",
            },
            "q3": {
                "question": "What type of pension does the Guaranteed Lifetime Income Plan provide?",
                "options": ["Variable pension", "Lifelong guaranteed pension", "Unit-linked pension", "Market-based pension"],
                "correct": "Lifelong guaranteed pension",
            },
        },
    },
    {
        "module_name": "Consultative Selling Approach",
        "module_category": "sales_techniques",
        "description": "Learn the need-based consultative selling methodology. Understand customer profiling, need analysis, product mapping, and closing techniques specific to insurance.",
        "learning_material": {
            "sections": [
                {
                    "title": "What is Consultative Selling?",
                    "content": "Consultative selling is a sales methodology where the agent acts as a trusted advisor rather than a product pusher. Instead of leading with product features, you lead with understanding the customer's needs, concerns, and financial goals. The product recommendation comes naturally as a solution to their specific situation.",
                },
                {
                    "title": "The 5-Step Consultative Sales Process",
                    "key_points": [
                        {"label": "Step 1: Build Rapport", "value": "Establish trust through genuine interest in the customer's life, family, and goals"},
                        {"label": "Step 2: Need Analysis", "value": "Use the Need Analysis Questionnaire to uncover protection gaps, savings goals, and risk appetite"},
                        {"label": "Step 3: Solution Mapping", "value": "Match identified needs to specific products — term for protection, ULIP for wealth, pension for retirement"},
                        {"label": "Step 4: Presentation", "value": "Present the solution as an answer to THEIR needs, not as a product pitch. Use benefit illustrations."},
                        {"label": "Step 5: Close", "value": "Summarize needs addressed, handle remaining objections, collect documents, submit e-proposal"},
                    ],
                },
                {
                    "title": "Need Analysis Questionnaire — Key Areas",
                    "bullets": [
                        "Family structure: married/single, number of dependents, spouse employment status",
                        "Income & expenses: monthly income, existing EMIs, monthly savings capacity",
                        "Existing insurance: employer cover, personal policies, total sum assured",
                        "Financial goals: children's education, home purchase, retirement, wealth creation",
                        "Risk appetite: conservative (savings plans), moderate (balanced ULIPs), aggressive (equity ULIPs)",
                    ],
                },
                {
                    "title": "Closing Techniques for Insurance",
                    "bullets": [
                        "Assumptive close: 'Since we've identified Rs 1 crore as your ideal cover, shall I prepare the proposal for regular pay or limited pay?'",
                        "Urgency close: 'Your premium at age 32 is Rs 8,500/year. By age 33, it increases to Rs 9,200. Locking in now saves Rs 21,000 over the policy term.'",
                        "Summary close: 'Let me summarize — we're addressing your protection gap of Rs 1 crore, your daughter's education fund, and Rs 50 lakh retirement corpus. All three with just Rs 25,000/month.'",
                    ],
                },
            ],
            "do_and_dont": {
                "do": [
                    "Always complete the need analysis before recommending any product",
                    "Use the benefit illustration tool to show personalized projections",
                    "Document the customer's stated needs — this is your compliance record",
                    "Follow up within 48 hours if the customer needs time to decide",
                ],
                "dont": [
                    "Never lead with 'We have a great offer running' — that's transactional selling",
                    "Don't recommend products that earn you higher commission but don't fit the customer's needs",
                    "Never pressure a customer into buying — it leads to early surrenders and complaints",
                    "Don't skip the need analysis for repeat customers — their needs change over time",
                ],
            },
            "target_audience": "All ADMs and agents — this is a foundational skill module",
            "estimated_reading_time": "9 minutes",
        },
        "questions": {
            "q1": {
                "question": "What is the first step in consultative selling?",
                "options": ["Present product features", "Understand customer needs", "Quote premium", "Close the sale"],
                "correct": "Understand customer needs",
            },
            "q2": {
                "question": "Which tool helps in matching customer needs to appropriate products?",
                "options": ["Premium calculator", "Need analysis questionnaire", "Competitor comparison sheet", "Commission chart"],
                "correct": "Need analysis questionnaire",
            },
            "q3": {
                "question": "What should an agent do when a customer raises a price objection?",
                "options": ["Offer a discount", "Shift focus to value and benefits", "Show a cheaper product", "End the conversation"],
                "correct": "Shift focus to value and benefits",
            },
        },
    },
    {
        "module_name": "Objection Handling Mastery",
        "module_category": "objection_handling",
        "description": "Master techniques for handling the top 10 customer objections in life insurance sales. Practice the LAER (Listen, Acknowledge, Explore, Respond) framework.",
        "learning_material": {
            "sections": [
                {
                    "title": "The LAER Framework",
                    "content": "LAER stands for Listen, Acknowledge, Explore, Respond. It is the gold standard for handling objections without becoming defensive or dismissive. Most agents fail because they immediately try to counter the objection. LAER teaches you to first understand the real concern behind the stated objection.",
                    "key_points": [
                        {"label": "Listen", "value": "Let the customer fully express their concern without interrupting. Nod and maintain eye contact."},
                        {"label": "Acknowledge", "value": "Show empathy: 'I understand your concern' or 'Many customers feel the same way initially.'"},
                        {"label": "Explore", "value": "Ask questions to understand the root cause: 'What specifically concerns you about the premium?'"},
                        {"label": "Respond", "value": "Address the real concern with facts, stories, and data. Not a generic pitch."},
                    ],
                },
                {
                    "title": "Top 5 Objections & LAER Responses",
                    "bullets": [
                        "'Insurance is a waste of money' → Acknowledge: 'I understand, many people feel that way.' Explore: 'Have you or anyone you know ever needed to make a claim?' Respond: Share a real claim settlement story, highlight the ~99.51% settlement ratio.",
                        "'I can't afford the premium' → Acknowledge: 'Budget is important.' Explore: 'What would a comfortable monthly amount look like?' Respond: Show a plan that fits their budget, or suggest starting with term insurance at Rs 500/month for Rs 1 crore cover.",
                        "'I need to discuss with my family' → Acknowledge: 'Absolutely, it's a family decision.' Explore: 'Would it help if I explain the plan to your spouse as well?' Respond: Offer a joint meeting, send a summary on WhatsApp for them to review together.",
                        "'My friend had a bad experience with insurance' → Acknowledge: 'I'm sorry to hear that.' Explore: 'What happened?' Respond: Most bad experiences are from mis-sold products. Explain your consultative approach and IRDAI's free-look period.",
                        "'I'll think about it' → Acknowledge: 'Take your time.' Explore: 'Is there a specific concern I haven't addressed?' Respond: Often means they have an unspoken objection. Try to surface it gently.",
                    ],
                },
            ],
            "do_and_dont": {
                "do": [
                    "Always listen fully before responding — never interrupt",
                    "Use real claim stories and data to build credibility",
                    "Keep a calm, empathetic tone throughout",
                    "Treat every objection as a buying signal — they're still talking to you",
                ],
                "dont": [
                    "Never argue with the customer or say 'You're wrong'",
                    "Don't take objections personally — they're about the product, not you",
                    "Never badmouth competitor products to win an argument",
                    "Don't give up after one objection — most sales close after handling 3-5 objections",
                ],
            },
            "target_audience": "All agents — this is the most critical skill for improving conversion rates",
            "estimated_reading_time": "8 minutes",
        },
        "questions": {
            "q1": {
                "question": "What does LAER stand for in objection handling?",
                "options": [
                    "Lead, Attract, Engage, Retain",
                    "Listen, Acknowledge, Explore, Respond",
                    "Learn, Adapt, Execute, Review",
                    "Locate, Analyze, Evaluate, Resolve",
                ],
                "correct": "Listen, Acknowledge, Explore, Respond",
            },
            "q2": {
                "question": "When a customer says 'Insurance is a waste of money', the best response is to:",
                "options": [
                    "Argue that they are wrong",
                    "Acknowledge their concern and share real claim stories",
                    "Offer a cheaper product",
                    "Move on to the next customer",
                ],
                "correct": "Acknowledge their concern and share real claim stories",
            },
            "q3": {
                "question": "What is the most common objection faced by insurance agents in India?",
                "options": ["Product features", "Premium affordability", "Company reputation", "Agent trust"],
                "correct": "Premium affordability",
            },
        },
    },
    {
        "module_name": "IRDAI Compliance Essentials",
        "module_category": "compliance",
        "description": "Understand key IRDAI regulations, disclosure requirements, free-look period, mis-selling prevention, and agent code of conduct.",
        "learning_material": {
            "sections": [
                {
                    "title": "Why Compliance Matters",
                    "content": "IRDAI (Insurance Regulatory and Development Authority of India) sets strict rules to protect policyholders. Non-compliance can result in license cancellation for agents, penalties for the company, and most importantly — harm to customers. As an ADM, ensuring your agents follow compliance norms is your primary regulatory responsibility.",
                },
                {
                    "title": "Key IRDAI Regulations",
                    "key_points": [
                        {"label": "Free-Look Period", "value": "15 days from policy receipt — customer can cancel for any reason and get a full refund (minus medical costs and stamp duty)"},
                        {"label": "ULIP Lock-in", "value": "5 years mandatory — no surrender or withdrawal allowed before this period"},
                        {"label": "Benefit Illustration", "value": "Must show two scenarios (4% and 8% return) for market-linked products — MANDATORY for every sale"},
                        {"label": "Cooling-off Period", "value": "30 days for online policies — extended free-look for digital purchases"},
                        {"label": "Disclosure Requirements", "value": "All charges, exclusions, and terms must be disclosed in writing before policy issuance"},
                    ],
                },
                {
                    "title": "What Counts as Mis-selling?",
                    "bullets": [
                        "Guaranteeing returns on market-linked products (ULIPs) — the biggest compliance violation",
                        "Not disclosing all charges and fees to the customer",
                        "Selling products that don't match the customer's stated needs or risk profile",
                        "Forging documents or signatures on proposal forms",
                        "Rebating — offering part of your commission to the customer as an incentive",
                        "Replacement selling — convincing customers to surrender existing policies to buy new ones for commission",
                    ],
                },
                {
                    "title": "Agent Code of Conduct",
                    "bullets": [
                        "Always carry your IRDAI license while meeting customers",
                        "Never collect cash premiums — use only digital/cheque payments",
                        "Complete mandatory training hours each year to maintain license",
                        "Report any suspicious activity or fraud attempts to your ADM immediately",
                    ],
                },
            ],
            "do_and_dont": {
                "do": [
                    "Always show the benefit illustration with both 4% and 8% scenarios",
                    "Inform every customer about the 15-day free-look period",
                    "Keep records of all customer interactions and disclosures",
                    "Report mis-selling by agents in your team immediately",
                ],
                "dont": [
                    "NEVER guarantee returns on any market-linked product",
                    "Never forge or manipulate proposal forms",
                    "Don't encourage policy surrenders for replacement with new policies",
                    "Never accept cash premiums from customers",
                ],
            },
            "target_audience": "All ADMs and agents — compliance is mandatory knowledge",
            "estimated_reading_time": "6 minutes",
        },
        "questions": {
            "q1": {
                "question": "What is the free-look period for life insurance policies in India?",
                "options": ["7 days", "15 days", "30 days", "45 days"],
                "correct": "15 days",
            },
            "q2": {
                "question": "Which of the following is considered mis-selling?",
                "options": [
                    "Explaining all product features",
                    "Guaranteeing returns on ULIP products",
                    "Sharing the benefit illustration",
                    "Disclosing all charges",
                ],
                "correct": "Guaranteeing returns on ULIP products",
            },
            "q3": {
                "question": "What is the IRDAI-mandated lock-in period for ULIPs?",
                "options": ["3 years", "5 years", "7 years", "10 years"],
                "correct": "5 years",
            },
        },
    },
    {
        "module_name": "Digital Sales Tools Training",
        "module_category": "digital_tools",
        "description": "Learn to use Max Life's digital ecosystem - mobile app, customer portal, benefit illustration tool, e-proposal submission, and video calling for remote sales.",
        "learning_material": {
            "sections": [
                {
                    "title": "The Digital Sales Ecosystem",
                    "content": "Axis Max Life has built a comprehensive digital toolkit that enables agents to sell, service, and support customers entirely online. Using these tools correctly can reduce turnaround time from weeks to hours, eliminate paper-related errors, and enable remote selling — critical in today's market.",
                },
                {
                    "title": "Tool Overview",
                    "key_points": [
                        {"label": "Benefit Illustration Tool", "value": "Generate personalized projections showing customers exactly what they'll get at maturity or death. MANDATORY for every sale."},
                        {"label": "e-Proposal", "value": "Digital proposal submission — faster processing, fewer errors, automatic data validation, instant acknowledgement"},
                        {"label": "Customer Portal", "value": "Self-service portal for customers — view policy details, download statements, submit service requests"},
                        {"label": "Mobile App", "value": "Agent app for on-the-go access — run illustrations, check lead status, submit proposals, track commissions"},
                        {"label": "Video Calling", "value": "Built-in video calling for remote meetings — screen share benefit illustrations, complete KYC via video"},
                    ],
                },
                {
                    "title": "Why e-Proposal Beats Paper",
                    "bullets": [
                        "Processing time reduced from 7-10 days to 24-48 hours",
                        "Automatic field validation eliminates 90% of common errors (wrong PAN format, incomplete addresses)",
                        "Digital signature via OTP — no physical signatures needed",
                        "Real-time tracking — both agent and customer can see exact status",
                        "Higher first-attempt approval rates (92% vs 68% for paper proposals)",
                    ],
                },
            ],
            "do_and_dont": {
                "do": [
                    "Always run a benefit illustration on the tool before every customer meeting",
                    "Use e-proposals instead of paper for faster processing",
                    "Train your agents to use the mobile app for lead management",
                    "Conduct remote meetings via video call for out-of-town customers",
                ],
                "dont": [
                    "Don't share your login credentials with agents",
                    "Never use personal WhatsApp for sharing customer documents — use the secure portal",
                    "Don't manually modify benefit illustration outputs",
                    "Never promise faster processing than the system actually delivers",
                ],
            },
            "target_audience": "All ADMs and agents — digital proficiency is now mandatory",
            "estimated_reading_time": "5 minutes",
        },
        "questions": {
            "q1": {
                "question": "Which tool should agents use to show customers their projected benefits?",
                "options": ["Premium calculator", "Benefit illustration tool", "Fund factsheet", "Policy brochure"],
                "correct": "Benefit illustration tool",
            },
            "q2": {
                "question": "What is the advantage of e-proposal submission over paper proposals?",
                "options": [
                    "Higher commission",
                    "Faster processing and fewer errors",
                    "No medical required",
                    "Automatic approval",
                ],
                "correct": "Faster processing and fewer errors",
            },
            "q3": {
                "question": "How can agents conduct remote sales meetings?",
                "options": [
                    "Only in-person meetings allowed",
                    "Through the app's video calling feature",
                    "Via email only",
                    "Through physical branch visit",
                ],
                "correct": "Through the app's video calling feature",
            },
        },
    },
    {
        "module_name": "Building Customer Relationships",
        "module_category": "soft_skills",
        "description": "Develop essential soft skills for long-term customer relationship management. Cover trust building, referral generation, post-sale service, and anniversary touchpoints.",
        "learning_material": {
            "sections": [
                {
                    "title": "The Lifetime Value of a Customer",
                    "content": "A single insurance customer can generate 10-15 policy purchases over their lifetime (term, savings, child plan, pension, health). Plus, each satisfied customer generates 3-5 referrals on average. The key is to build a relationship that lasts beyond the first sale. Most agents focus on acquisition and ignore retention — this is why their business plateaus.",
                },
                {
                    "title": "The Customer Touchpoint Calendar",
                    "key_points": [
                        {"label": "Day 1-7", "value": "Welcome call — confirm policy receipt, explain key features, introduce yourself as their advisor"},
                        {"label": "Day 30", "value": "Check-in call — any questions about the policy? Explain the free-look period is over."},
                        {"label": "Quarterly", "value": "Value-add touch — share market updates, tax planning tips, new product info"},
                        {"label": "Policy Anniversary", "value": "Birthday + anniversary wishes, review coverage adequacy, discuss life changes"},
                        {"label": "Life Events", "value": "Marriage, baby, job change, home purchase — each is a trigger for additional coverage"},
                    ],
                },
                {
                    "title": "Referral Generation Best Practices",
                    "bullets": [
                        "Best time to ask: after claim settlement or maturity payout — the customer has seen the value",
                        "Second-best time: during the annual review when the customer is already engaged",
                        "Never cold-ask for referrals — earn them through consistent service first",
                        "Make it easy: 'Would your brother/colleague benefit from a similar plan? I can offer them the same guidance.'",
                        "Thank referral sources — a small gesture (card, call) reinforces the behavior",
                    ],
                },
            ],
            "do_and_dont": {
                "do": [
                    "Maintain a touchpoint calendar for every customer in your CRM",
                    "Ask for referrals after delivering value, never before",
                    "Remember personal details — children's names, milestones, preferences",
                    "Be available for service queries even when there's no sale involved",
                ],
                "dont": [
                    "Don't disappear after the first sale — this destroys trust permanently",
                    "Never call only when you have something to sell",
                    "Don't share customer details with third parties without consent",
                    "Never over-promise on claim timelines or policy features",
                ],
            },
            "target_audience": "All agents looking to build sustainable, referral-driven business",
            "estimated_reading_time": "7 minutes",
        },
        "questions": {
            "q1": {
                "question": "What is the most effective way to generate referrals?",
                "options": [
                    "Cold calling random numbers",
                    "Asking satisfied customers after claim settlement or maturity",
                    "Buying lead lists",
                    "Social media advertising",
                ],
                "correct": "Asking satisfied customers after claim settlement or maturity",
            },
            "q2": {
                "question": "When should an agent contact a customer after policy issuance?",
                "options": [
                    "Only at renewal time",
                    "Within 7 days and then at regular intervals",
                    "Never unless customer calls",
                    "Only when new products launch",
                ],
                "correct": "Within 7 days and then at regular intervals",
            },
            "q3": {
                "question": "What is the key to building long-term trust with customers?",
                "options": [
                    "Offering the cheapest premium",
                    "Consistent communication and transparent advice",
                    "Gifting during festivals",
                    "Promising highest returns",
                ],
                "correct": "Consistent communication and transparent advice",
            },
        },
    },
    {
        "module_name": "Need-Based Selling",
        "module_category": "sales_techniques",
        "description": "Learn to identify and map customer needs to appropriate insurance solutions. Cover life stage analysis, financial goal mapping, and gap analysis techniques.",
        "learning_material": {
            "sections": [
                {
                    "title": "Life Stage Product Mapping",
                    "content": "Different life stages have different insurance needs. A structured approach to need identification prevents mis-selling and ensures customer satisfaction. The right product at the right life stage creates trust and generates referrals.",
                    "key_points": [
                        {"label": "Age 22-28 (Young Single)", "value": "Term Insurance (income replacement for parents), ULIP for wealth creation — start with low premiums"},
                        {"label": "Age 28-35 (New Family)", "value": "Term Insurance (primary), Child Plan (for new baby), Savings Plan (systematic wealth building)"},
                        {"label": "Age 35-45 (Peak Earning)", "value": "Increase term cover, ULIPs (wealth boosters kick in), Child plan top-ups, start Pension planning"},
                        {"label": "Age 45-55 (Pre-Retirement)", "value": "Pension Plan (primary), Guaranteed Income Plan, reduce equity exposure in ULIPs"},
                        {"label": "Age 55+ (Retirement)", "value": "Annuity products, Senior Citizen health plans, corpus distribution planning"},
                    ],
                },
                {
                    "title": "Human Life Value (HLV) Method",
                    "content": "HLV calculates the adequate life insurance cover based on the economic value a person represents to their family. Formula: (Annual Income - Personal Expenses) x Remaining Working Years x Inflation Factor. A 30-year-old earning Rs 15 lakh/year with 30 working years remaining has an HLV of approximately Rs 2-3 crore. This method prevents both under-insurance and over-insurance.",
                },
                {
                    "title": "Gap Analysis Technique",
                    "bullets": [
                        "Step 1: Calculate total financial needs (HLV + children's education + spouse's support + loan liabilities)",
                        "Step 2: Subtract existing coverage (employer insurance + existing personal policies + savings)",
                        "Step 3: The gap = coverage needed from new policies",
                        "Step 4: Split the gap across appropriate products (term for protection, ULIP for growth, savings for guarantees)",
                        "Always present the gap analysis in writing — it builds credibility and serves as a compliance document",
                    ],
                },
            ],
            "do_and_dont": {
                "do": [
                    "Always perform HLV calculation before recommending sum assured",
                    "Map each product recommendation to a specific identified need",
                    "Document the need analysis — it's your compliance protection",
                    "Review coverage annually — life changes mean need changes",
                ],
                "dont": [
                    "Never recommend a product without understanding the customer's life stage",
                    "Don't sell pension plans to 25-year-olds or aggressive ULIPs to 55-year-olds",
                    "Never ignore existing coverage — it leads to over-insurance complaints",
                    "Don't use HLV as a pressure tactic ('You're under-insured by Rs 2 crore!') — present it as an educational tool",
                ],
            },
            "target_audience": "All ADMs and agents — foundational skill for ethical, need-based selling",
            "estimated_reading_time": "8 minutes",
        },
        "questions": {
            "q1": {
                "question": "For a young married couple with a new baby, which product category should be the PRIMARY recommendation?",
                "options": ["Pension plan", "Term insurance + child plan", "ULIP only", "Health insurance only"],
                "correct": "Term insurance + child plan",
            },
            "q2": {
                "question": "What is the Human Life Value (HLV) method used for?",
                "options": [
                    "Calculating investment returns",
                    "Determining adequate life cover amount",
                    "Setting premium rates",
                    "Evaluating fund performance",
                ],
                "correct": "Determining adequate life cover amount",
            },
            "q3": {
                "question": "For a 50-year-old planning retirement in 10 years, which product fits best?",
                "options": [
                    "Term insurance",
                    "Child plan",
                    "Guaranteed Lifetime Income Plan",
                    "ULIP with aggressive fund",
                ],
                "correct": "Guaranteed Lifetime Income Plan",
            },
        },
    },
    {
        "module_name": "Claims Process Navigation",
        "module_category": "compliance",
        "description": "Understand the end-to-end claims process for death claims, maturity claims, and survival benefits. Learn documentation requirements and turnaround times.",
        "learning_material": {
            "sections": [
                {
                    "title": "Claims Settlement — The Moment of Truth",
                    "content": "The claims process is when insurance delivers on its promise. Axis Max Life's claims settlement ratio of ~99.51% is among the highest in the industry. As an ADM, your role is to ensure agents guide families smoothly through what is often the most difficult time of their lives. A well-handled claim creates lifelong loyalty and referrals.",
                },
                {
                    "title": "Types of Claims",
                    "key_points": [
                        {"label": "Death Claim", "value": "Filed by nominee/beneficiary on death of policyholder. Should be filed as soon as possible — there is no strict time limit by law."},
                        {"label": "Maturity Claim", "value": "Automatic payout at end of policy term. Company initiates contact 2-3 months before maturity. Customer provides bank details."},
                        {"label": "Survival Benefit", "value": "Periodic payouts during policy term (e.g., Guaranteed Smart Income Plan). Automatically credited to customer's account."},
                        {"label": "Rider Claims", "value": "Critical illness, accidental disability — filed with diagnosis/hospital reports. Policy may continue after rider claim."},
                    ],
                },
                {
                    "title": "Death Claim — Required Documents",
                    "bullets": [
                        "Death Certificate (primary document — mandatory)",
                        "Original policy document (or indemnity bond if lost)",
                        "Claimant's ID proof (Aadhaar/PAN) and bank details",
                        "FIR/Post-mortem report (if death is unnatural/accidental)",
                        "Medical records/hospital discharge summary (if death due to illness)",
                        "NEFT mandate form for electronic fund transfer",
                    ],
                },
                {
                    "title": "ADM's Role in Claims",
                    "bullets": [
                        "Be the first point of contact for the bereaved family — reach out within 24 hours",
                        "Help the family gather required documents — don't leave them to figure it out alone",
                        "Coordinate with the claims department for status updates",
                        "Follow up until the claim is settled — typical TAT is 7-15 days for uncomplicated claims",
                        "After settlement, the family becomes your strongest referral source — handle with empathy",
                    ],
                },
            ],
            "do_and_dont": {
                "do": [
                    "Reach out to the nominee family within 24 hours of learning about a claim",
                    "Help compile all required documents — create a checklist for the family",
                    "Keep the family updated on claim status at every stage",
                    "Use the ~99.51% settlement ratio as a trust-building point during sales",
                ],
                "dont": [
                    "Never delay in initiating a death claim — time sensitivity matters for the family",
                    "Don't ask for unnecessary documents that aren't in the standard checklist",
                    "Never discuss sales or new policies during the claim process — focus on service only",
                    "Don't make verbal promises about claim timelines — share realistic TATs",
                ],
            },
            "target_audience": "All ADMs and agents — claim handling is a critical service skill",
            "estimated_reading_time": "6 minutes",
        },
        "questions": {
            "q1": {
                "question": "What is Axis Max Life's claims settlement ratio?",
                "options": ["~95%", "~97%", "~99.51%", "100%"],
                "correct": "~99.51%",
            },
            "q2": {
                "question": "Within how many days should a death claim be filed?",
                "options": ["30 days", "90 days", "As soon as possible, no strict limit", "1 year"],
                "correct": "As soon as possible, no strict limit",
            },
            "q3": {
                "question": "What is the primary document needed for a death claim?",
                "options": ["PAN card", "Death certificate", "Aadhaar card", "Bank statement"],
                "correct": "Death certificate",
            },
        },
    },
]

# Build a quick lookup
MODULE_LOOKUP = {m["module_name"]: m for m in TRAINING_MODULES}


@router.get("/modules", response_model=List[TrainingModuleInfo])
def list_training_modules():
    """List all available training modules."""
    return [
        TrainingModuleInfo(
            module_name=m["module_name"],
            module_category=m["module_category"],
            description=m["description"],
            questions_count=len(m["questions"]),
        )
        for m in TRAINING_MODULES
    ]


@router.get("/modules/{module_name}")
def get_module_detail(module_name: str):
    """
    Get detailed information about a training module including quiz questions.
    Note: correct answers are NOT returned - only question text and options.
    """
    module = MODULE_LOOKUP.get(module_name)
    if not module:
        # Try fuzzy match
        for name, mod in MODULE_LOOKUP.items():
            if module_name.lower() in name.lower():
                module = mod
                break

    if not module:
        raise HTTPException(status_code=404, detail=f"Module '{module_name}' not found")

    # Return questions without correct answers
    questions = {}
    for qid, qdata in module["questions"].items():
        questions[qid] = {
            "question": qdata["question"],
            "options": qdata["options"],
        }

    return {
        "module_name": module["module_name"],
        "module_category": module["module_category"],
        "description": module["description"],
        "questions_count": len(module["questions"]),
        "questions": questions,
        "learning_material": module.get("learning_material"),
    }


@router.post("/quiz/submit")
def submit_quiz(data: QuizAnswer, db: Session = Depends(get_db)):
    """
    Submit quiz answers for a training module.
    Calculates score based on correct answers and saves progress.
    """
    # Validate ADM
    adm = db.query(ADM).filter(ADM.id == data.adm_id).first()
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    # Find the module
    module = MODULE_LOOKUP.get(data.module_name)
    if not module:
        raise HTTPException(status_code=404, detail=f"Module '{data.module_name}' not found")

    # Grade the answers
    total_questions = len(module["questions"])
    correct_count = 0
    results = {}

    for qid, selected_answer in data.answers.items():
        if qid in module["questions"]:
            correct = module["questions"][qid]["correct"]
            is_correct = selected_answer == correct
            if is_correct:
                correct_count += 1
            results[qid] = {
                "selected": selected_answer,
                "correct": correct,
                "is_correct": is_correct,
            }

    score = round((correct_count / total_questions * 100), 1) if total_questions > 0 else 0
    passed = score >= 70  # 70% passing threshold

    # Save or update progress
    existing = db.query(TrainingProgress).filter(
        TrainingProgress.adm_id == data.adm_id,
        TrainingProgress.module_name == data.module_name,
    ).first()

    if existing:
        # Update only if new score is higher
        if score > existing.score:
            existing.score = score
            existing.completed = passed
            if passed:
                existing.completed_at = datetime.utcnow()
    else:
        progress = TrainingProgress(
            adm_id=data.adm_id,
            module_name=data.module_name,
            module_category=data.module_category or module["module_category"],
            score=score,
            completed=passed,
            completed_at=datetime.utcnow() if passed else None,
        )
        db.add(progress)

    db.commit()

    return {
        "module_name": data.module_name,
        "adm_id": data.adm_id,
        "total_questions": total_questions,
        "correct_answers": correct_count,
        "score": score,
        "passed": passed,
        "passing_threshold": 70,
        "results": results,
    }


@router.get("/progress/{adm_id}")
def get_training_progress(adm_id: int, db: Session = Depends(get_db)):
    """
    Get an ADM's training progress across all modules.
    Shows completed, in-progress, and not-started modules.
    """
    adm = db.query(ADM).filter(ADM.id == adm_id).first()
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    progress_records = db.query(TrainingProgress).filter(
        TrainingProgress.adm_id == adm_id,
    ).all()

    progress_map = {p.module_name: p for p in progress_records}

    total_modules = len(TRAINING_MODULES)
    completed_modules = sum(1 for p in progress_records if p.completed)
    in_progress_modules = sum(1 for p in progress_records if not p.completed)
    not_started = total_modules - len(progress_records)
    total_score = sum(p.score for p in progress_records)
    avg_score = round(total_score / len(progress_records), 1) if progress_records else 0

    modules_detail = []
    for m in TRAINING_MODULES:
        progress = progress_map.get(m["module_name"])
        if progress:
            modules_detail.append({
                "module_name": m["module_name"],
                "module_category": m["module_category"],
                "status": "completed" if progress.completed else "in_progress",
                "score": progress.score,
                "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
            })
        else:
            modules_detail.append({
                "module_name": m["module_name"],
                "module_category": m["module_category"],
                "status": "not_started",
                "score": 0,
                "completed_at": None,
            })

    return {
        "adm_id": adm_id,
        "adm_name": adm.name,
        "total_modules": total_modules,
        "completed": completed_modules,
        "in_progress": in_progress_modules,
        "not_started": not_started,
        "average_score": avg_score,
        "overall_progress_pct": round((completed_modules / total_modules * 100), 1) if total_modules > 0 else 0,
        "modules": modules_detail,
    }


@router.get("/leaderboard", response_model=List[LeaderboardEntry])
def get_training_leaderboard(db: Session = Depends(get_db)):
    """
    Get training leaderboard ranking ADMs by their training performance.
    Sorted by total score (sum of all module scores) descending.
    """
    adms = db.query(ADM).all()
    total_modules = len(TRAINING_MODULES)
    leaderboard = []

    for adm in adms:
        progress_records = db.query(TrainingProgress).filter(
            TrainingProgress.adm_id == adm.id,
        ).all()

        completed = sum(1 for p in progress_records if p.completed)
        # Use average score (not sum) to keep scores in 0-100% range
        avg_score = round(
            sum(p.score for p in progress_records) / len(progress_records), 1
        ) if progress_records else 0

        leaderboard.append(
            LeaderboardEntry(
                adm_id=adm.id,
                adm_name=adm.name,
                region=adm.region,
                total_score=avg_score,
                modules_completed=completed,
                total_modules=total_modules,
            )
        )

    # Sort by average score descending
    leaderboard.sort(key=lambda x: x.total_score, reverse=True)
    return leaderboard
