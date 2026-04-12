"""
TechPrep Telegram Bot — steps 8 & 9.

Run:
    source .venv/bin/activate
    python -m backend.bot.telegram_bot

Commands:
    /start    — welcome + plan selection
    /link     — link this Telegram account to your web app account
    /plan     — switch active plan
    /practice — start a practice session (feedback after each answer)
    /mock     — start a mock interview (all feedback at the end)
    /stop     — end current session
    /skip     — skip current question (grade 0)

Voice messages are transcribed via OpenAI Whisper before evaluation.
"""

import asyncio
import logging
import os
import re
import secrets
import hashlib
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from ..database import SessionLocal
from .. import models
from ..agents import interview_agent, teacher_agent
from ..services.sm2 import update_sm2
from ..services.transcription import transcribe_audio
from ..routers.interview import _next_question, _is_dont_know


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── In-memory session state per Telegram user ─────────────────────────────────
# { telegram_id: { session_id, question, user_id, plan_id, mode, mock_log, count } }
_state: dict[int, dict] = {}

# Pending mode when user needs to pick a plan before starting
# { telegram_id: mode }
_pending_mode: dict[int, str] = {}

GRADE_LABEL = ["Blackout", "Familiar", "Recalled", "Correct", "Good", "Perfect"]
GRADE_EMOJI = ["❌", "🔴", "🟠", "🟡", "🟢", "⭐"]
DIFF_LABEL  = {1: "Beginner", 2: "Easy", 3: "Medium", 4: "Hard", 5: "Expert"}

_MD2_SPECIAL = re.compile(r'([_*\[\]()~`>#+\-=|{}.!\\])')

def _e(text: str) -> str:
    """Escape a string for Telegram MarkdownV2."""
    return _MD2_SPECIAL.sub(r'\\\1', str(text))


# ── DB helpers ────────────────────────────────────────────────────────────────

def _db():
    return SessionLocal()


def _get_or_create_user(db, telegram_id: int) -> models.User:
    user = db.query(models.User).filter(models.User.telegram_id == telegram_id).first()
    if not user:
        user = models.User(
            email=f"telegram_{telegram_id}@techprep.bot",
            hashed_password=hashlib.sha256(secrets.token_bytes(32)).hexdigest(),
            telegram_id=telegram_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _get_plans(db, user_id: int) -> list[models.Plan]:
    return db.query(models.Plan).filter(models.Plan.user_id == user_id).all()


def _teacher_severity(db, user_id: int, plan_id: int) -> int:
    row = db.query(models.Setting).filter(
        models.Setting.plan_id == plan_id,
        models.Setting.key == "teacher_severity",
    ).first()
    return int(row.value) if row else 2


# ── Message formatting ────────────────────────────────────────────────────────

def _fmt_question(q: models.Question) -> str:
    return (
        f"📌 *{_e(q.theme.name)}* · {_e(DIFF_LABEL.get(q.difficulty, '?'))} "
        f"· {_e(q.type.replace('_', ' ').title())}\n\n"
        f"{_e(q.content)}"
    )


def _plan_keyboard(plans: list[models.Plan], prefix: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(p.name, callback_data=f"{prefix}:{p.id}")]
        for p in plans
    ]
    return InlineKeyboardMarkup(buttons)


# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    db = _db()
    try:
        user = _get_or_create_user(db, tg_id)
        plans = _get_plans(db, user.id)

        if not plans:
            await update.message.reply_text(
                "👋 *Welcome to TechPrep\\!*\n\n"
                "You don't have any study plans yet\\.\n"
                "Open the web app to create one, then come back here to practice\\.",
                parse_mode="MarkdownV2",
            )
            return

        now = datetime.utcnow()
        total = db.query(models.QuestionProgress).filter(
            models.QuestionProgress.user_id == user.id
        ).count()
        due = db.query(models.QuestionProgress).filter(
            models.QuestionProgress.user_id == user.id,
            models.QuestionProgress.next_review_at <= now,
        ).count()
        new_q = db.query(models.QuestionProgress).filter(
            models.QuestionProgress.user_id == user.id,
            models.QuestionProgress.status == "new",
        ).count()

        plans_list = "\n".join(f"  • {_e(p.name)}" for p in plans)

        await update.message.reply_text(
            f"👋 *Welcome to TechPrep\\!*\n\n"
            f"📊 Your stats \\(all plans\\):\n"
            f"  • Questions: {total}\n"
            f"  • Due today: {due}\n"
            f"  • New: {new_q}\n\n"
            f"📚 Your plans:\n{plans_list}\n\n"
            f"*Commands:*\n"
            f"  /link — link to your web app account\n"
            f"  /plan — select active plan\n"
            f"  /practice — practice session \\(feedback after each answer\\)\n"
            f"  /mock — mock interview \\(feedback at the end\\)\n"
            f"  /stop — end current session\n"
            f"  /skip — skip current question",
            parse_mode="MarkdownV2",
        )
    finally:
        db.close()


async def cmd_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    db = _db()
    try:
        user = _get_or_create_user(db, tg_id)
        plans = _get_plans(db, user.id)
        if not plans:
            await update.message.reply_text(
                "No plans found\\. Create one in the web app first\\.",
                parse_mode="MarkdownV2",
            )
            return
        await update.message.reply_text(
            "Select a plan:",
            reply_markup=_plan_keyboard(plans, "plan"),
        )
    finally:
        db.close()


async def cmd_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text(
            "Usage: `/link 123456`\n\nGet your code from the TechPrep web app → Connect Telegram.",
            parse_mode="Markdown",
        )
        return

    code = context.args[0].strip()
    db = _db()
    try:
        link = db.query(models.TelegramLinkCode).filter(
            models.TelegramLinkCode.code == code,
        ).first()

        if not link:
            await update.message.reply_text("❌ Invalid code. Generate a new one in the web app.")
            return

        if link.expires_at < datetime.utcnow():
            db.delete(link)
            db.commit()
            await update.message.reply_text("❌ Code expired. Generate a new one in the web app.")
            return

        web_user = db.query(models.User).filter(models.User.id == link.user_id).first()
        if not web_user:
            await update.message.reply_text("❌ User not found.")
            return

        if web_user.telegram_id and web_user.telegram_id != tg_id:
            await update.message.reply_text("❌ This account is already linked to a different Telegram user.")
            return

        # Delete any placeholder bot-user created for this Telegram ID
        bot_user = db.query(models.User).filter(
            models.User.telegram_id == tg_id,
            models.User.id != web_user.id,
        ).first()
        if bot_user:
            db.delete(bot_user)
            db.flush()  # flush DELETE before setting telegram_id to avoid UNIQUE conflict

        web_user.telegram_id = tg_id
        db.delete(link)
        db.commit()

        plans = db.query(models.Plan).filter(models.Plan.user_id == web_user.id).all()
        plan_names = "\n".join(f"  • {_e(p.name)}" for p in plans) or "  \\(none yet\\)"
        await update.message.reply_text(
            f"✅ Account linked successfully\\!\n\n"
            f"📚 Your plans:\n{plan_names}\n\n"
            f"Use /practice or /mock to start a session\\.",
            parse_mode="MarkdownV2",
        )
    finally:
        db.close()


async def cmd_practice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _start_or_pick_plan(update, "practice")


async def cmd_mock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _start_or_pick_plan(update, "mock")


async def _start_or_pick_plan(update: Update, mode: str):
    tg_id = update.effective_user.id
    db = _db()
    try:
        user = _get_or_create_user(db, tg_id)
        plans = _get_plans(db, user.id)

        if not plans:
            await update.message.reply_text(
                "No plans found\\. Create one in the web app first\\.",
                parse_mode="MarkdownV2",
            )
            return

        if len(plans) == 1:
            # Only one plan — use it directly
            await _start_session(update, mode, user.id, plans[0].id)
            return

        # Multiple plans — ask user to pick
        _pending_mode[tg_id] = mode
        await update.message.reply_text(
            f"Select a plan for this {mode} session:",
            reply_markup=_plan_keyboard(plans, "session"),
        )
    finally:
        db.close()


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tg_id = query.from_user.id
    data = query.data  # "plan:<id>" or "session:<id>"

    prefix, plan_id_str = data.split(":", 1)
    plan_id = int(plan_id_str)

    db = _db()
    try:
        user = _get_or_create_user(db, tg_id)
        plan = db.query(models.Plan).filter(
            models.Plan.id == plan_id,
            models.Plan.user_id == user.id,
        ).first()
        if not plan:
            await query.edit_message_text("Plan not found.")
            return

        if prefix == "plan":
            # Just switching the plan display
            await query.edit_message_text(f"✅ Active plan set to: *{plan.name}*", parse_mode="Markdown")
            # Store plan selection in state for next session
            if tg_id in _state:
                _state[tg_id]["plan_id"] = plan_id

        elif prefix == "session":
            mode = _pending_mode.pop(tg_id, "practice")
            await query.edit_message_text(f"Starting {mode} session with plan: *{plan.name}*…", parse_mode="Markdown")
            await _start_session(update, mode, user.id, plan_id)
    finally:
        db.close()


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    if tg_id not in _state:
        await update.message.reply_text("No active session\\.", parse_mode="MarkdownV2")
        return

    state = _state.pop(tg_id)
    db = _db()
    try:
        session = db.query(models.Session).filter(
            models.Session.id == state["session_id"]
        ).first()
        if session and not session.ended_at:
            session.ended_at = datetime.utcnow()
            db.commit()

        if state["mode"] == "mock" and state["mock_log"]:
            await _send_mock_review(update, state["mock_log"])
        else:
            await update.message.reply_text("✅ Session ended\\.", parse_mode="MarkdownV2")
    finally:
        db.close()


async def cmd_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    if tg_id not in _state:
        await update.message.reply_text(
            "No active session\\. Start with /practice or /mock\\.",
            parse_mode="MarkdownV2",
        )
        return
    await _process_answer(update, tg_id, answer_text="[skipped]", skip=True)


# ── Message handlers ──────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    if tg_id not in _state:
        await update.message.reply_text(
            "No active session\\. Start with /practice or /mock\\.",
            parse_mode="MarkdownV2",
        )
        return
    await _process_answer(update, tg_id, answer_text=update.message.text)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    if tg_id not in _state:
        await update.message.reply_text(
            "No active session\\. Start with /practice or /mock\\.",
            parse_mode="MarkdownV2",
        )
        return

    await update.message.reply_text("🎤 Transcribing…")
    try:
        voice = update.message.voice or update.message.audio
        tg_file = await context.bot.get_file(voice.file_id)
        file_bytes = bytes(await tg_file.download_as_bytearray())

        text = await asyncio.to_thread(transcribe_audio, file_bytes, "ogg")
        await update.message.reply_text(f"_Transcribed:_ {text}", parse_mode="Markdown")
        await _process_answer(update, tg_id, answer_text=text)
    except Exception as exc:
        logger.exception("Transcription failed")
        await update.message.reply_text(f"⚠️ Transcription failed: {exc}")


# ── Session start ─────────────────────────────────────────────────────────────

async def _start_session(update: Update, mode: str, user_id: int, plan_id: int):
    tg_id = update.effective_user.id
    db = _db()
    try:
        # Use the right message target (could be callback query or regular message)
        msg_target = (
            update.callback_query.message
            if update.callback_query
            else update.message
        )

        # Close any existing session
        if tg_id in _state:
            old = _state.pop(tg_id)
            old_session = db.query(models.Session).filter(
                models.Session.id == old["session_id"]
            ).first()
            if old_session and not old_session.ended_at:
                old_session.ended_at = datetime.utcnow()
                db.commit()

        session = models.Session(user_id=user_id, type=mode, plan_id=plan_id)
        db.add(session)
        db.commit()
        db.refresh(session)

        question = _next_question(db, user_id, plan_id, session.id)
        if not question:
            session.ended_at = datetime.utcnow()
            db.commit()
            await msg_target.reply_text(
                "📭 No questions available in this plan yet\\!\n\n"
                "Use the web app Coach to generate some first\\.",
                parse_mode="MarkdownV2",
            )
            return

        _state[tg_id] = {
            "session_id": session.id,
            "question": question,
            "user_id": user_id,
            "plan_id": plan_id,
            "mode": mode,
            "mock_log": [],
            "count": 1,
        }

        label = "🎯 *Practice session*" if mode == "practice" else "⏱ *Mock interview*"
        await msg_target.reply_text(
            f"{label} started\\!\n\n"
            f"{_fmt_question(question)}\n\n"
            f"_Type your answer or send a voice message\\._",
            parse_mode="MarkdownV2",
        )
    finally:
        db.close()


# ── Core answer processing ────────────────────────────────────────────────────

async def _process_answer(
    update: Update,
    tg_id: int,
    answer_text: str,
    skip: bool = False,
):
    state      = _state[tg_id]
    question   = state["question"]
    session_id = state["session_id"]
    user_id    = state["user_id"]
    plan_id    = state["plan_id"]
    mode       = state["mode"]
    is_retry   = state.pop("awaiting_retry", False)

    await update.message.reply_text("⏳ Evaluating…")

    db = _db()
    try:
        severity = _teacher_severity(db, user_id, plan_id)

        if skip:
            evaluation = {
                "feedback": "Question skipped.",
                "grade": 0,
            }
        elif _is_dont_know(answer_text):
            evaluation = {"feedback": "No answer provided.", "grade": 0}
        else:
            evaluation = await asyncio.to_thread(
                interview_agent.evaluate,
                question.content,
                answer_text,
                severity,
                is_retry,
            )

        grade = evaluation["grade"]

        # Persist answer
        answer = models.Answer(
            session_id=session_id,
            question_id=question.id,
            content=answer_text,
            ai_feedback=evaluation["feedback"],
            sm2_grade=grade,
        )
        db.add(answer)
        db.flush()

        # Apply SM-2
        progress = db.query(models.QuestionProgress).filter(
            models.QuestionProgress.question_id == question.id,
            models.QuestionProgress.user_id == user_id,
        ).first()
        if not progress:
            progress = models.QuestionProgress(
                question_id=question.id, user_id=user_id
            )
            db.add(progress)
            db.flush()
        update_sm2(progress, grade)
        db.commit()

        # Fetch or generate explanation for poor first attempts (not retries, not mock)
        explanation = None
        if not is_retry and not skip and grade <= 2 and mode == "practice":
            if question.explanation:
                explanation = question.explanation
            else:
                try:
                    explanation = await asyncio.to_thread(teacher_agent.explain, question.content)
                    question.explanation = explanation
                    db.commit()
                except Exception:
                    logger.error("teacher_agent failed for question %s", question.id, exc_info=True)

        # Get next question before sending feedback
        next_q = _next_question(db, user_id, plan_id, session_id)

        if mode == "practice":
            msg = (
                f"{GRADE_EMOJI[grade]} *{_e(GRADE_LABEL[grade])}* \\({grade}/5\\)\n"
                f"Next review: {_e(progress.interval_days)}d · Status: {_e(progress.status)}\n\n"
                f"{_e(evaluation['feedback'])}"
            )
            if explanation:
                msg += f"\n\n📖 *Model Explanation:*\n{_e(explanation)}"
            await update.message.reply_text(msg, parse_mode="MarkdownV2")

            # Offer retry if first poor attempt
            if not skip and not state.get("awaiting_retry") and grade <= 2 and explanation:
                state["awaiting_retry"] = True
                await update.message.reply_text(
                    "🔄 *Give it another shot\\!*\n\nNow that you've seen the explanation, try answering again\\.",
                    parse_mode="MarkdownV2",
                )
                return  # Don't advance yet
        else:
            state["mock_log"].append({
                "question": question.content,
                "answer": answer_text,
                "feedback": evaluation["feedback"],
                "grade": grade,
                "explanation": explanation,
            })
            count = len(state["mock_log"])
            await update.message.reply_text(f"✅ Answer {count} recorded\\.", parse_mode="MarkdownV2")

        # Advance or close session
        if next_q:
            state["question"] = next_q
            await update.message.reply_text(
                f"{_fmt_question(next_q)}\n\n_Type your answer or send a voice message\\._",
                parse_mode="MarkdownV2",
            )
        else:
            session = db.query(models.Session).filter(
                models.Session.id == session_id
            ).first()
            if session and not session.ended_at:
                session.ended_at = datetime.utcnow()
                db.commit()

            mock_log = state.get("mock_log", [])
            del _state[tg_id]

            if mode == "mock" and mock_log:
                await _send_mock_review(update, mock_log)
            else:
                await update.message.reply_text(
                    "🎉 Session complete\\! No more questions due\\.\n\n"
                    "Use /practice to start a new session\\.",
                    parse_mode="MarkdownV2",
                )
    finally:
        db.close()


# ── Mock review ───────────────────────────────────────────────────────────────

async def _send_mock_review(update: Update, mock_log: list):
    msg_target = (
        update.callback_query.message
        if update.callback_query
        else update.message
    )
    await msg_target.reply_text("📋 *Mock Interview Results*", parse_mode="MarkdownV2")

    for i, entry in enumerate(mock_log, 1):
        g = entry["grade"]
        q_preview = entry["question"][:120] + ("…" if len(entry["question"]) > 120 else "")
        msg = (
            f"*Q{i}:* {_e(q_preview)}\n\n"
            f"{GRADE_EMOJI[g]} *{_e(GRADE_LABEL[g])}* \\({g}/5\\)\n\n"
            f"{_e(entry['feedback'])}"
        )
        if entry.get("explanation"):
            msg += f"\n\n📖 *Model Explanation:*\n{_e(entry['explanation'])}"
        await msg_target.reply_text(msg, parse_mode="MarkdownV2")

    total = len(mock_log)
    avg = sum(e["grade"] for e in mock_log) / total if total else 0
    await msg_target.reply_text(
        f"📊 *Summary:* {total} questions · avg grade {avg:.1f}/5",
        parse_mode="MarkdownV2",
    )


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in the environment.")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("link",     cmd_link))
    app.add_handler(CommandHandler("plan",     cmd_plan))
    app.add_handler(CommandHandler("practice", cmd_practice))
    app.add_handler(CommandHandler("mock",     cmd_mock))
    app.add_handler(CommandHandler("stop",     cmd_stop))
    app.add_handler(CommandHandler("skip",     cmd_skip))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    logger.info("TechPrep bot starting (polling)…")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
