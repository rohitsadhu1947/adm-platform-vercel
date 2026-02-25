"""
Training conversation handler for the ADM Platform Telegram Bot.
Product category -> Product selection -> AI summary -> Quiz flow.
"""

import logging
from telegram import Update
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from config import TrainingStates
from utils.api_client import api_client
from utils.formatters import (
    format_product_summary,
    format_quiz_question,
    format_quiz_result,
    error_generic,
    error_not_registered,
    cancelled,
    header,
    section_divider,
    E_BOOK, E_BRAIN, E_CHECK, E_CROSS, E_STAR,
    E_SHIELD, E_MONEY, E_CHART, E_ELDER, E_BABY,
    E_PEOPLE, E_SPARKLE, E_FIRE, E_TROPHY, E_MEDAL,
    E_THUMBSUP, E_TARGET, E_DIAMOND, E_WARNING,
    E_PIN, E_ROCKET, E_BULB, E_MUSCLE,
)
from utils.keyboards import (
    training_category_keyboard,
    training_product_keyboard,
    quiz_start_keyboard,
    quiz_answer_keyboard,
)
from utils.voice import send_voice_response

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Category labels for display
# ---------------------------------------------------------------------------
CATEGORY_MAP = {
    "tcat_term": ("Term Insurance", "term"),
    "tcat_savings": ("Savings Plans", "savings"),
    "tcat_ulip": ("ULIPs", "ulip"),
    "tcat_pension": ("Pension Plans", "pension"),
    "tcat_child": ("Child Plans", "child"),
    "tcat_group": ("Group Insurance", "group"),
}



# ---------------------------------------------------------------------------
# Entry: /train
# ---------------------------------------------------------------------------

async def train_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the training flow - show product categories."""
    telegram_id = update.effective_user.id

    profile = await api_client.get_adm_profile(telegram_id)
    if not profile or profile.get("error"):
        await update.message.reply_text(
            error_not_registered(), parse_mode="HTML",
        )
        return ConversationHandler.END

    train_intro = (
        f"{E_BOOK} <b>Product Training / Praduct Training</b>\n\n"
        f"{E_STAR} Select a product category to learn:\n"
        f"Ek category chunein seekhne ke liye:\n\n"
        f"{E_SPARKLE} <i>Learn products, ace the quiz, and become a selling expert!</i>"
    )
    sent_msg = await update.message.reply_text(
        train_intro,
        parse_mode="HTML",
        reply_markup=training_category_keyboard(),
    )
    await send_voice_response(sent_msg, train_intro)
    return TrainingStates.SELECT_CATEGORY


# ---------------------------------------------------------------------------
# Step 1: Category selected -> show products
# ---------------------------------------------------------------------------

async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle category selection - show products in that category."""
    query = update.callback_query
    await query.answer()

    data = query.data

    # Handle back to categories
    if data == "tcat_back":
        await query.edit_message_text(
            f"{E_BOOK} <b>Product Training / Praduct Training</b>\n\n"
            f"{E_STAR} Select a product category to learn:\n"
            f"Ek category chunein seekhne ke liye:",
            parse_mode="HTML",
            reply_markup=training_category_keyboard(),
        )
        return TrainingStates.SELECT_CATEGORY

    if data not in CATEGORY_MAP:
        await query.edit_message_text(error_generic(), parse_mode="HTML")
        return ConversationHandler.END

    cat_label, cat_key = CATEGORY_MAP[data]
    context.user_data["train"] = {"category": cat_key, "category_label": cat_label}

    # Fetch products from backend API
    products_resp = await api_client.get_training_products(cat_key)
    products = products_resp.get("products", products_resp.get("data", []))

    if not products:
        await query.edit_message_text(
            f"{E_WARNING} No products found in <b>{cat_label}</b>.\n"
            f"Is category mein abhi koi product nahi hai.\n\n"
            f"Try another category with /train",
            parse_mode="HTML",
        )
        return ConversationHandler.END

    context.user_data["train"]["products_cache"] = products

    # Category emoji mapping
    cat_emojis = {
        "term": E_SHIELD, "savings": E_MONEY, "ulip": E_CHART,
        "pension": E_ELDER, "child": E_BABY, "group": E_PEOPLE,
    }
    cat_emoji = cat_emojis.get(cat_key, E_BOOK)

    await query.edit_message_text(
        f"{cat_emoji} <b>{cat_label}</b>\n\n"
        f"{E_STAR} Select a product to learn about:\n"
        f"Product chunein details ke liye:\n\n"
        f"<i>Products: {len(products)}</i>",
        parse_mode="HTML",
        reply_markup=training_product_keyboard(products, cat_key),
    )
    return TrainingStates.SELECT_PRODUCT


# ---------------------------------------------------------------------------
# Step 2: Product selected -> show AI summary
# ---------------------------------------------------------------------------

async def select_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle product selection - show AI-generated summary."""
    query = update.callback_query
    await query.answer()

    data = query.data

    # Handle back to categories
    if data == "tcat_back":
        await query.edit_message_text(
            f"{E_BOOK} <b>Product Training</b>\n\n"
            f"{E_STAR} Select a product category:",
            parse_mode="HTML",
            reply_markup=training_category_keyboard(),
        )
        return TrainingStates.SELECT_CATEGORY

    product_id = data.replace("tprod_", "")
    products = context.user_data.get("train", {}).get("products_cache", [])

    # Find product name
    product_name = "Unknown Product"
    product_category = context.user_data.get("train", {}).get("category_label", "")
    for prod in products:
        if str(prod.get("id", "")) == product_id:
            product_name = prod.get("name", "Unknown Product")
            product_category = prod.get("category", product_category)
            break

    context.user_data["train"]["product_id"] = product_id
    context.user_data["train"]["product_name"] = product_name

    # Show loading message
    await query.edit_message_text(
        f"{E_BRAIN} <b>Loading product details...</b>\n\n"
        f"<i>{product_name} ki jaankari load ho rahi hai...</i>",
        parse_mode="HTML",
    )

    # Fetch product summary from backend API
    summary_resp = await api_client.get_product_summary(product_id)
    summary_data = summary_resp if not summary_resp.get("error") else None

    if not summary_data:
        await query.edit_message_text(
            f"{E_WARNING} <b>Product details not available</b>\n\n"
            f"<i>{product_name}</i> ki details abhi load nahi ho payi.\n"
            f"Please try again with /train",
            parse_mode="HTML",
        )
        return ConversationHandler.END

    formatted = format_product_summary(summary_data)

    await query.edit_message_text(
        formatted,
        parse_mode="HTML",
        reply_markup=quiz_start_keyboard(),
    )
    # Send voice for product summary (key learning content)
    await send_voice_response(query.message, formatted)
    return TrainingStates.VIEW_SUMMARY


# ---------------------------------------------------------------------------
# Step 3: Quiz start
# ---------------------------------------------------------------------------

async def view_summary_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle actions from product summary view (quiz start or back)."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "quiz_back":
        # Go back to product list
        train_data = context.user_data.get("train", {})
        cat_key = train_data.get("category", "term")
        cat_label = train_data.get("category_label", "Term Insurance")
        products = train_data.get("products_cache", [])

        if products:
            await query.edit_message_text(
                f"{E_BOOK} <b>{cat_label}</b>\n\n"
                f"{E_STAR} Select a product to learn about:",
                parse_mode="HTML",
                reply_markup=training_product_keyboard(products, cat_key),
            )
            return TrainingStates.SELECT_PRODUCT
        else:
            await query.edit_message_text(
                f"{E_BOOK} <b>Product Training</b>\n\n"
                f"{E_STAR} Select a product category:",
                parse_mode="HTML",
                reply_markup=training_category_keyboard(),
            )
            return TrainingStates.SELECT_CATEGORY

    if data == "quiz_start":
        return await _start_quiz(query, context)

    return TrainingStates.VIEW_SUMMARY


async def _start_quiz(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initialize and show the first quiz question."""
    train_data = context.user_data.get("train", {})
    product_id = train_data.get("product_id", "")
    product_name = train_data.get("product_name", "Product")

    # Fetch quiz from backend API
    quiz_resp = await api_client.get_quiz(product_id)
    quiz_data = quiz_resp if not quiz_resp.get("error") else None

    if not quiz_data:
        await query.edit_message_text(
            f"{E_WARNING} <b>Quiz not available</b>\n\n"
            f"<i>{product_name}</i> ka quiz load nahi ho paya.\n"
            f"Please try again with /train",
            parse_mode="HTML",
        )
        return ConversationHandler.END

    questions = quiz_data.get("questions", [])

    if not questions:
        await query.edit_message_text(
            f"{E_WARNING} No quiz available for <b>{product_name}</b>.\n"
            f"Is product ke liye abhi quiz nahi hai.\n\n"
            f"Use /train to try another product.",
            parse_mode="HTML",
        )
        return ConversationHandler.END

    context.user_data["train"]["quiz_questions"] = questions
    context.user_data["train"]["quiz_current"] = 0
    context.user_data["train"]["quiz_score"] = 0

    # Show first question
    q = questions[0]
    total = len(questions)

    await query.edit_message_text(
        f"{E_BRAIN} <b>Quiz Time! / Quiz ka Samay!</b>\n"
        f"<i>Product: {product_name}</i>\n\n"
        f"{section_divider()}"
        f"{format_quiz_question(q, 1, total)}",
        parse_mode="HTML",
        reply_markup=quiz_answer_keyboard(q.get("options", [])),
    )
    return TrainingStates.ANSWER_QUIZ


# ---------------------------------------------------------------------------
# Step 4: Answer quiz questions
# ---------------------------------------------------------------------------

async def answer_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle quiz answer selection."""
    query = update.callback_query
    await query.answer()

    data = query.data  # e.g., "quiz_ans_0", "quiz_ans_1", etc.

    if not data.startswith("quiz_ans_"):
        return TrainingStates.ANSWER_QUIZ

    selected_idx = int(data.replace("quiz_ans_", ""))

    train_data = context.user_data.get("train", {})
    questions = train_data.get("quiz_questions", [])
    current = train_data.get("quiz_current", 0)
    score = train_data.get("quiz_score", 0)
    product_name = train_data.get("product_name", "Product")

    if current >= len(questions):
        return await _show_quiz_result(query, context)

    q = questions[current]
    correct_idx = q.get("correct", 0)
    options = q.get("options", [])

    # Check answer
    is_correct = selected_idx == correct_idx
    if is_correct:
        score += 1
        context.user_data["train"]["quiz_score"] = score

    # Build answer feedback
    selected_text = options[selected_idx] if selected_idx < len(options) else "?"
    correct_text = options[correct_idx] if correct_idx < len(options) else "?"

    if is_correct:
        feedback = f"{E_CHECK} <b>Correct! / Sahi Jawab!</b> {E_SPARKLE}\n"
    else:
        feedback = (
            f"{E_CROSS} <b>Incorrect / Galat</b>\n"
            f"Your answer: {selected_text}\n"
            f"{E_CHECK} Correct answer: <b>{correct_text}</b>\n"
        )

    # Move to next question or show result
    next_idx = current + 1
    context.user_data["train"]["quiz_current"] = next_idx

    if next_idx >= len(questions):
        # Show final result
        total = len(questions)
        result_text = format_quiz_result(score, total)

        from utils.keyboards import training_category_keyboard as tck

        # Build result keyboard
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        result_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E_BRAIN} Retake Quiz / Dobara Quiz", callback_data="quiz_retake")],
            [InlineKeyboardButton(f"{E_BOOK} More Products / Aur Products", callback_data="tcat_back")],
            [InlineKeyboardButton(f"{E_CHECK} Done / Ho Gaya", callback_data="cancel")],
        ])

        full_result = f"{feedback}\n{section_divider()}{result_text}"
        await query.edit_message_text(
            full_result,
            parse_mode="HTML",
            reply_markup=result_keyboard,
        )
        await send_voice_response(query.message, full_result)
        return TrainingStates.QUIZ_RESULT
    else:
        # Show next question
        next_q = questions[next_idx]
        total = len(questions)

        await query.edit_message_text(
            f"{feedback}\n"
            f"Score so far: <b>{score}/{next_idx}</b>\n"
            f"{section_divider()}"
            f"{format_quiz_question(next_q, next_idx + 1, total)}",
            parse_mode="HTML",
            reply_markup=quiz_answer_keyboard(next_q.get("options", [])),
        )
        return TrainingStates.ANSWER_QUIZ


# ---------------------------------------------------------------------------
# Step 5: Quiz result actions
# ---------------------------------------------------------------------------

async def quiz_result_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle actions from quiz result screen."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "quiz_retake":
        # Reset quiz and restart
        context.user_data["train"]["quiz_current"] = 0
        context.user_data["train"]["quiz_score"] = 0
        return await _start_quiz(query, context)

    if data == "tcat_back":
        # Back to category selection
        await query.edit_message_text(
            f"{E_BOOK} <b>Product Training</b>\n\n"
            f"{E_STAR} Select a product category:",
            parse_mode="HTML",
            reply_markup=training_category_keyboard(),
        )
        return TrainingStates.SELECT_CATEGORY

    # Cancel / Done
    complete_text = (
        f"{E_CHECK} <b>Training session complete!</b>\n\n"
        f"Bahut achha! Training session khatam hua. {E_SPARKLE}\n"
        f"Use /train anytime to learn more!\n\n"
        f"{E_MUSCLE} Keep learning, keep growing! {E_FIRE}"
    )
    await query.edit_message_text(
        complete_text,
        parse_mode="HTML",
    )
    await send_voice_response(query.message, complete_text)

    # Submit score to backend
    train_data = context.user_data.get("train", {})
    score = train_data.get("quiz_score", 0)
    product_id = train_data.get("product_id", "")
    telegram_id = update.effective_user.id

    try:
        await api_client.submit_quiz_result({
            "adm_telegram_id": telegram_id,
            "product_id": product_id,
            "score": score,
            "total": len(train_data.get("quiz_questions", [])),
        })
    except Exception:
        pass  # Non-critical, don't break the flow

    context.user_data.pop("train", None)
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

async def cancel_training(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel training flow."""
    context.user_data.pop("train", None)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(cancelled(), parse_mode="HTML")
    else:
        await update.message.reply_text(cancelled(), parse_mode="HTML")

    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Build ConversationHandler
# ---------------------------------------------------------------------------

def build_training_handler() -> ConversationHandler:
    """Build the /train conversation handler."""
    return ConversationHandler(
        entry_points=[CommandHandler("train", train_command)],
        states={
            TrainingStates.SELECT_CATEGORY: [
                CallbackQueryHandler(select_category, pattern=r"^tcat_"),
            ],
            TrainingStates.SELECT_PRODUCT: [
                CallbackQueryHandler(select_product, pattern=r"^tprod_"),
                CallbackQueryHandler(select_category, pattern=r"^tcat_"),
            ],
            TrainingStates.VIEW_SUMMARY: [
                CallbackQueryHandler(view_summary_action, pattern=r"^quiz_"),
            ],
            TrainingStates.ANSWER_QUIZ: [
                CallbackQueryHandler(answer_quiz, pattern=r"^quiz_ans_"),
            ],
            TrainingStates.QUIZ_RESULT: [
                CallbackQueryHandler(quiz_result_action, pattern=r"^(quiz_retake|tcat_back|cancel)$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_training),
            CallbackQueryHandler(cancel_training, pattern=r"^cancel$"),
        ],
        name="training",
        persistent=True,
    )
