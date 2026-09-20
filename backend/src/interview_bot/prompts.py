from interview_bot.domain import Difficulty, Question, Topic

TOPIC_LABELS = {
    Topic.PYTHON: "Python",
    Topic.REACT: "React",
    Topic.JAVASCRIPT: "JavaScript",
}

DIFFICULTY_LABELS = {
    Difficulty.JUNIOR: "a junior engineer with about a year of experience",
    Difficulty.MID: "a mid-level engineer with three to five years of experience",
    Difficulty.SENIOR: "a senior engineer who designs systems and mentors others",
}

GENERATE_SYSTEM = (
    "You are a senior software engineer conducting a technical interview. "
    "You reply with JSON only, never with prose or markdown fences."
)

GRADE_SYSTEM = (
    "You are a fair, concise technical interviewer grading a candidate's answer. "
    "You reply with JSON only, never with prose or markdown fences."
)


def generate_prompt(*, topic: Topic, difficulty: Difficulty, avoid: list[str]) -> str:
    avoid_block = ""
    if avoid:
        already_asked = "\n".join(f"- {prompt}" for prompt in avoid)
        avoid_block = (
            "\n\nYou have already asked the questions below. "
            f"Ask about something clearly different.\n{already_asked}"
        )

    return (
        f"Ask one {TOPIC_LABELS[topic]} interview question suitable for "
        f"{DIFFICULTY_LABELS[difficulty]}."
        f"\n\nThe question must be specifically about {TOPIC_LABELS[topic]} itself — its syntax, "
        "semantics, standard library, tooling or ecosystem. A question that would read the same "
        "way for any other language or framework is not acceptable."
        "\n\nThe question must be answerable in a few sentences of prose. "
        "Do not ask the candidate to write code."
        "\n\nAlso list the key points a complete answer covers. "
        "Give three to five of them, each a short phrase."
        f"{avoid_block}"
        "\n\nRespond with JSON shaped exactly like: "
        '{"question": "...", "key_points": ["...", "..."]}'
    )


def grade_prompt(*, question: Question, answer: str) -> str:
    key_points = "\n".join(f"- {point}" for point in question.key_points)
    return (
        f"Question asked:\n{question.prompt}"
        f"\n\nKey points a complete answer covers:\n{key_points}"
        f"\n\nThe candidate answered:\n{answer}"
        "\n\nScore the answer from 0 to 5, where 0 is no useful content, "
        "3 is a workable answer with gaps, and 5 is complete and correct. "
        "Judge the substance, not the wording or length. "
        "If the answer is off topic or empty, score it 0."
        "\n\nWrite the verdict as one or two sentences addressed to the candidate. "
        "List the key points they covered and the ones they missed."
        "\n\nRespond with JSON shaped exactly like: "
        '{"score": 3, "verdict": "...", "covered": ["..."], "missed": ["..."]}'
    )
