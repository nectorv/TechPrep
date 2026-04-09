from datetime import datetime, timedelta
from ..models import QuestionProgress


def update_sm2(progress: QuestionProgress, grade: int) -> QuestionProgress:
    """
    Apply SM-2 algorithm after a graded answer.

    grade: 0-5 (returned by the interviewer agent)
      0 = complete blackout
      1 = incorrect, topic seemed familiar
      2 = incorrect, recalled after seeing solution
      3 = correct with significant difficulty
      4 = correct after slight hesitation
      5 = perfect, immediate and precise
    """
    if grade >= 3:
        if progress.repetitions == 0:
            progress.interval_days = 1
        elif progress.repetitions == 1:
            progress.interval_days = 6
        else:
            progress.interval_days = round(progress.interval_days * progress.ef)
        progress.repetitions += 1
    else:
        progress.repetitions = 0
        progress.interval_days = 1

    # Update easiness factor (floor at 1.3)
    progress.ef = max(
        1.3,
        progress.ef + 0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02),
    )

    # Derive status
    if progress.repetitions == 0:
        progress.status = "new"
    elif progress.repetitions <= 2:
        progress.status = "learning"
    else:
        progress.status = "acquired"

    progress.last_reviewed_at = datetime.utcnow()
    progress.next_review_at = datetime.utcnow() + timedelta(days=progress.interval_days)
    return progress
