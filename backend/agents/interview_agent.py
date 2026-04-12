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
   - 1: major misunderstanding of the topic
   - 2: on the right track but fundamentally incomplete or wrong
   - 3: correct but missing important details or context
   - 4: solid answer — covers the core concept well, minor gaps acceptable
   - 5: complete and confident — no significant gaps

Always respond with ONLY this JSON (no prose outside the object):
{{
  "feedback": "<feedback text>",
  "grade": <integer 0-5>
}}"""

_SYSTEM_RETRY_TEMPLATE = """\
You are a technical interviewer evaluating a SECOND ATTEMPT.

The candidate previously failed this question and was shown a model explanation.
They are now trying again based on what they just learned.

Your goal is to assess whether they understood the concept — not whether they could
have answered cold. Be generous: if they demonstrate understanding of the core idea,
award a high grade even if their wording is imperfect or they missed minor details.

Feedback severity: {severity}/5 (apply leniently — this is a learning retry)

Grading for a retry:
  - 5: demonstrates clear understanding of the concept
  - 4: mostly correct, minor gaps or wording issues
  - 3: partial understanding — got the gist but missed key parts
  - 2 or below: still fundamentally wrong despite seeing the explanation

Give brief, encouraging feedback (under 80 words):
  - Focus on what they got right
  - Note any remaining gaps briefly

Always respond with ONLY this JSON (no prose outside the object):
{{
  "feedback": "<feedback text>",
  "grade": <integer 0-5>
}}"""


def evaluate(question_content: str, answer: str, teacher_severity: int = 2, is_retry: bool = False) -> dict:
    """
    Evaluate a candidate's answer to a technical question.
    Returns a dict: {feedback, grade}
    """
    severity = max(1, min(5, teacher_severity))
    template = _SYSTEM_RETRY_TEMPLATE if is_retry else _SYSTEM_TEMPLATE
    system = template.format(severity=severity)

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
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw)
