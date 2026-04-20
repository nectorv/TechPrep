import os
import json
import time
from datetime import datetime
from anthropic import Anthropic, APIStatusError
from sqlalchemy.orm import Session
from .. import models
from ..services.question_gen import generate_questions

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-20250514"

TOOLS = [
    {
        "name": "add_questions",
        "description": "Generate and add a batch of questions to the DB for a given theme",
        "input_schema": {
            "type": "object",
            "properties": {
                "theme_id":   {"type": "integer"},
                "count":      {"type": "integer", "description": "Number of questions to generate (max 20)"},
                "difficulty": {"type": "integer", "minimum": 1, "maximum": 5},
                "type":       {"type": "string", "enum": ["concept", "algo", "system_design", "behavioral"]},
            },
            "required": ["theme_id", "count", "difficulty", "type"],
        },
    },
    {
        "name": "add_specific_question",
        "description": "Add a single manually specified question to the DB for a given theme",
        "input_schema": {
            "type": "object",
            "properties": {
                "theme_id":   {"type": "integer"},
                "content":    {"type": "string", "description": "The exact question text"},
                "difficulty": {"type": "integer", "minimum": 1, "maximum": 5},
                "type":       {"type": "string", "enum": ["concept", "algo", "system_design", "behavioral"]},
            },
            "required": ["theme_id", "content", "difficulty", "type"],
        },
    },
    {
        "name": "delete_question",
        "description": "Delete a question by its ID",
        "input_schema": {
            "type": "object",
            "properties": {
                "question_id": {"type": "integer"},
            },
            "required": ["question_id"],
        },
    },
    {
        "name": "list_questions",
        "description": "List questions in this plan, filterable by theme, difficulty, or status",
        "input_schema": {
            "type": "object",
            "properties": {
                "theme_id":   {"type": "integer"},
                "difficulty": {"type": "integer"},
                "status":     {"type": "string", "enum": ["new", "learning", "acquired"]},
            },
        },
    },
    {
        "name": "add_theme",
        "description": "Create a new theme or sub-theme in this plan",
        "input_schema": {
            "type": "object",
            "properties": {
                "name":      {"type": "string"},
                "parent_id": {"type": "integer"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "update_settings",
        "description": "Update a plan setting (daily_goal, teacher_severity, preferred_channel, session_length). teacher_severity must be an integer 1-5.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key":   {"type": "string"},
                "value": {"type": "string"},
            },
            "required": ["key", "value"],
        },
    },
    {
        "name": "get_study_overview",
        "description": "Return a summary for this plan: themes, question count by status, upcoming reviews",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


# ── Tool handlers ─────────────────────────────────────────────────────────────

def _add_theme(inp: dict, db: Session, user_id: int, plan_id: int) -> str:
    theme = models.Theme(
        user_id=user_id,
        plan_id=plan_id,
        name=inp["name"],
        parent_id=inp.get("parent_id"),
    )
    db.add(theme)
    db.commit()
    db.refresh(theme)
    return json.dumps({"theme_id": theme.id, "name": theme.name})


def _add_questions(inp: dict, db: Session, user_id: int, plan_id: int) -> str:
    theme = (
        db.query(models.Theme)
        .filter(
            models.Theme.id == inp["theme_id"],
            models.Theme.user_id == user_id,
            models.Theme.plan_id == plan_id,
        )
        .first()
    )
    if not theme:
        return json.dumps({"error": "Theme not found in this plan"})

    count = min(inp["count"], 20)
    try:
        questions_data = generate_questions(
            theme_name=theme.name,
            count=count,
            difficulty=inp["difficulty"],
            q_type=inp["type"],
        )
    except Exception as e:
        return json.dumps({"error": f"Question generation failed: {e}"})

    created = []
    for q in questions_data:
        question = models.Question(
            theme_id=theme.id,
            content=q["content"],
            difficulty=q["difficulty"],
            type=q["type"],
        )
        db.add(question)
        db.flush()
        db.add(models.QuestionProgress(question_id=question.id, user_id=user_id))
        created.append({"id": question.id, "content": q["content"][:120]})

    db.commit()
    result = {"created": len(created), "preview": created[:3]}
    if len(created) > 3:
        result["note"] = f"Showing first 3 of {len(created)}"
    return json.dumps(result)


def _add_specific_question(inp: dict, db: Session, user_id: int, plan_id: int) -> str:
    theme = (
        db.query(models.Theme)
        .filter(
            models.Theme.id == inp["theme_id"],
            models.Theme.user_id == user_id,
            models.Theme.plan_id == plan_id,
        )
        .first()
    )
    if not theme:
        return json.dumps({"error": "Theme not found in this plan"})

    question = models.Question(
        theme_id=theme.id,
        content=inp["content"],
        difficulty=inp["difficulty"],
        type=inp["type"],
    )
    db.add(question)
    db.flush()
    db.add(models.QuestionProgress(question_id=question.id, user_id=user_id))
    db.commit()
    return json.dumps({"id": question.id, "content": inp["content"][:120]})


def _delete_question(inp: dict, db: Session, user_id: int, plan_id: int) -> str:
    question = (
        db.query(models.Question)
        .join(models.Theme)
        .filter(
            models.Question.id == inp["question_id"],
            models.Theme.user_id == user_id,
            models.Theme.plan_id == plan_id,
        )
        .first()
    )
    if not question:
        return json.dumps({"error": "Question not found in this plan"})
    db.delete(question)
    db.commit()
    return json.dumps({"deleted": inp["question_id"]})


def _list_questions(inp: dict, db: Session, user_id: int, plan_id: int) -> str:
    query = (
        db.query(models.Question)
        .join(models.Theme)
        .filter(models.Theme.user_id == user_id, models.Theme.plan_id == plan_id)
    )
    if inp.get("theme_id") is not None:
        query = query.filter(models.Question.theme_id == inp["theme_id"])
    if inp.get("difficulty") is not None:
        query = query.filter(models.Question.difficulty == inp["difficulty"])
    if inp.get("status") is not None:
        query = (
            query.join(models.QuestionProgress)
            .filter(
                models.QuestionProgress.status == inp["status"],
                models.QuestionProgress.user_id == user_id,
            )
        )
    questions = query.limit(20).all()
    return json.dumps([
        {"id": q.id, "content": q.content[:120], "difficulty": q.difficulty, "type": q.type}
        for q in questions
    ])


def _update_settings(inp: dict, db: Session, user_id: int, plan_id: int) -> str:
    setting = (
        db.query(models.Setting)
        .filter(models.Setting.plan_id == plan_id, models.Setting.key == inp["key"])
        .first()
    )
    if setting:
        setting.value = inp["value"]
    else:
        db.add(models.Setting(
            user_id=user_id, plan_id=plan_id,
            key=inp["key"], value=inp["value"],
        ))
    db.commit()
    return json.dumps({"key": inp["key"], "value": inp["value"]})


def _get_study_overview(db: Session, user_id: int, plan_id: int) -> str:
    themes = (
        db.query(models.Theme)
        .filter(models.Theme.user_id == user_id, models.Theme.plan_id == plan_id)
        .all()
    )
    now = datetime.utcnow()
    overview = []
    for theme in themes:
        question_ids = [q.id for q in theme.questions]
        status_counts = {"new": 0, "learning": 0, "acquired": 0}
        due_count = 0
        if question_ids:
            for p in db.query(models.QuestionProgress).filter(
                models.QuestionProgress.question_id.in_(question_ids),
                models.QuestionProgress.user_id == user_id,
            ).all():
                status_counts[p.status] = status_counts.get(p.status, 0) + 1
                if p.next_review_at and p.next_review_at <= now:
                    due_count += 1
        overview.append({
            "theme": theme.name, "id": theme.id,
            "total": len(question_ids), "status": status_counts, "due_today": due_count,
        })

    settings = {
        s.key: s.value
        for s in db.query(models.Setting).filter(models.Setting.plan_id == plan_id).all()
    }
    return json.dumps({"themes": overview, "settings": settings})


def _dispatch_tool(name: str, inp: dict, db: Session, user_id: int, plan_id: int) -> str:
    if name == "get_study_overview":
        return _get_study_overview(db, user_id, plan_id)
    handlers = {
        "add_theme":             _add_theme,
        "add_questions":         _add_questions,
        "add_specific_question": _add_specific_question,
        "delete_question":       _delete_question,
        "list_questions":        _list_questions,
        "update_settings":       _update_settings,
    }
    if name in handlers:
        return handlers[name](inp, db, user_id, plan_id)
    return json.dumps({"error": f"Unknown tool: {name}"})


# ── System prompt ─────────────────────────────────────────────────────────────

def _build_system_prompt(db: Session, user_id: int, plan_id: int) -> str:
    themes = (
        db.query(models.Theme)
        .filter(models.Theme.user_id == user_id, models.Theme.plan_id == plan_id)
        .all()
    )
    settings = db.query(models.Setting).filter(models.Setting.plan_id == plan_id).all()

    themes_str = (
        "\n".join(f"  - {t.name} (id={t.id})" for t in themes) or "  No themes yet."
    )
    settings_str = (
        "\n".join(f"  {s.key} = {s.value}" for s in settings) or "  No settings yet."
    )

    return (
        "You are a job interview preparation coach.\n"
        "You help the user build and manage their study plan by creating relevant themes and questions.\n\n"
        "Your questions will be used in a smart flashcard system that grades the user's answers and schedules reviews based on an SM-2 algorithm.\n"
        "You have access to a question database via your tools.\n"
        "When the user asks you to generate questions on a topic, "
        "propose questions based on the themes in their plan. "
        "Always confirm the theme and question parameters before generating, then "
        "use add_questions and provide a preview of what was created.\n\n"
        "IMPORTANT: Never call add_questions for more than 3 themes in a single response. "
        "If the user asks to generate questions for many themes at once, do 3 at a time "
        "and tell the user to ask again to continue with the next batch.\n\n"
        "User context: professional preparing for job interviews.\n\n"
        f"Themes in this plan:\n{themes_str}\n\n"
        f"Current settings:\n{settings_str}\n\n"
        "Be proactive:\n"
        "- If the user mentions a theme that doesn't exist yet, offer to create it.\n"
        "- If the number of questions on a theme seems insufficient, flag it.\n"
        "- After each action, give a clear summary of what was done."
    )


# ── Main entry point ──────────────────────────────────────────────────────────

def run(user_message: str, db: Session, user_id: int, plan_id: int) -> str:
    db.add(models.CoachMessage(
        user_id=user_id, plan_id=plan_id, role="user", content=user_message,
    ))
    db.commit()

    history = (
        db.query(models.CoachMessage)
        .filter(
            models.CoachMessage.user_id == user_id,
            models.CoachMessage.plan_id == plan_id,
        )
        .order_by(models.CoachMessage.created_at)
        .all()
    )
    messages = [{"role": m.role, "content": m.content} for m in history]
    system_prompt = _build_system_prompt(db, user_id, plan_id)

    while True:
        for attempt in range(4):
            try:
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=4096,
                    system=system_prompt,
                    tools=TOOLS,
                    messages=messages,
                )
                break
            except APIStatusError as e:
                if e.status_code == 529 and attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                reply = "The AI is overloaded right now. Please try again in a few seconds."
                db.add(models.CoachMessage(
                    user_id=user_id, plan_id=plan_id, role="assistant", content=reply,
                ))
                db.commit()
                return reply

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            text = next((b.text for b in response.content if hasattr(b, "text")), "")
            db.add(models.CoachMessage(
                user_id=user_id, plan_id=plan_id, role="assistant", content=text,
            ))
            db.commit()
            return text

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = _dispatch_tool(block.name, block.input, db, user_id, plan_id)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return "An unexpected error occurred in the coach agent."
