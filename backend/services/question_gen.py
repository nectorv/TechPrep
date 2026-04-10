import os
import json
import time
from anthropic import Anthropic, APIStatusError

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-20250514"


def generate_questions(theme_name: str, count: int, difficulty: int, q_type: str) -> list[dict]:
    """
    Call Claude to generate `count` interview questions for a given theme.
    Returns a list of dicts: [{content, difficulty, type}, ...]
    """
    prompt = (
        f'You are an expert in technical interviews for software engineers.\n'
        f'Generate exactly {count} questions of type "{q_type}" on the topic "{theme_name}", '
        f'with a difficulty of {difficulty}/5.\n\n'
        f'Respond ONLY with a valid JSON array, no markdown, no comments.\n'
        f'Expected format:\n'
        f'[\n'
        f'  {{\n'
        f'    "content": "question text",\n'
        f'    "difficulty": {difficulty},\n'
        f'    "type": "{q_type}"\n'
        f'  }}\n'
        f']\n\n'
        f'Rules:\n'
        f'- Questions must be precise and typical of a real technical interview.\n'
        f'- Difficulty 1 = beginner, 5 = senior expert.\n'
        f'- For algo questions, include a complexity constraint where relevant.\n'
        f'- Do not number the questions inside the content field.'
    )

    for attempt in range(4):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            break
        except APIStatusError as e:
            if e.status_code == 529 and attempt < 3:
                time.sleep(2 ** attempt)  # 1s, 2s, 4s
                continue
            raise

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)
