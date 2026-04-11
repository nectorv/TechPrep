import os
import json
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-20250514"

_SYSTEM_TEMPLATE = """\
You are a technical interviewer for a software engineer position.
You evaluate candidates' answers to technical questions.

Feedback severity: {severity}/5
  1 = very encouraging, highlight positives, be forgiving of small gaps
  3 = balanced, note strengths and areas to improve
  5 = demanding, flag every inaccuracy and missing detail

For each answer you must:
1. Give feedback formatted for easy reading on a mobile screen:
   - Use short paragraphs (2-3 sentences max)
   - Use "✅ Strengths:" and "⚠️ To improve:" as section headers
   - Use "• " bullet points for lists — never long prose blocks
   - Keep the total feedback under 120 words
2. Assign an SM-2 grade between 0 and 5:
   - 0: complete blackout — no meaningful answer
   - 1: incorrect, but topic seemed familiar
   - 2: incorrect, but candidate could recall after seeing solution
   - 3: correct with significant difficulty or important gaps
   - 4: correct after slight hesitation or minor gaps
   - 5: perfect — immediate, precise, complete

Always respond with ONLY this JSON (no prose outside the object):
{{
  "feedback": "<feedback text>",
  "grade": <integer 0-5>
}}"""


def evaluate(question_content: str, answer: str, teacher_severity: int = 2) -> dict:
    """
    Evaluate a candidate's answer to a technical question.

    Returns a dict: {feedback, grade, correct_answer_hint}
    """
    severity = max(1, min(5, teacher_severity))
    system = _SYSTEM_TEMPLATE.format(severity=severity)

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Question: {question_content}\n\n"
                    f"Candidate's answer: {answer}"
                ),
            }
        ],
    )

    raw = response.content[0].text.strip()
    # Strip markdown fences defensively
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw)
