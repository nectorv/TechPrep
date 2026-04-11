import os
import json
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-20250514"

_SYSTEM = """\
You are a patient, beginner-friendly teacher explaining technical concepts to someone \
who is preparing for software engineering interviews.

Your job is to explain the correct answer to an interview question clearly and concisely.

Rules:
- Write for someone encountering this topic for the first time
- Use simple language — avoid jargon unless you define it
- Structure your explanation with short paragraphs
- Include a concrete example or analogy when it helps
- Keep it under 200 words total
- Do NOT evaluate the user's answer — focus only on teaching the concept

Always respond with ONLY this JSON (no prose outside the object):
{
  "explanation": "<your beginner-friendly explanation>"
}"""


def explain(question_content: str) -> str:
    """
    Generate a beginner-friendly explanation for the correct answer to a question.
    Returns the explanation string.
    """
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Interview question: {question_content}",
            }
        ],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw)["explanation"]
