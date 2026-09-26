import json


def question_reply(question: str = "What is the GIL?", key_points: list[str] | None = None) -> str:
    return json.dumps({"question": question, "key_points": key_points or ["a mutex", "one thread"]})


def grade_reply(score: int = 3, verdict: str = "Solid start.") -> str:
    return json.dumps(
        {"score": score, "verdict": verdict, "covered": ["a mutex"], "missed": ["one thread"]}
    )


def explanation_reply(answer: str = "The GIL is a mutex.\n\nOnly one thread runs bytecode.") -> str:
    return json.dumps(
        {
            "answer": answer,
            "points": [{"point": "a mutex", "detail": "It guards the interpreter state."}],
            "pitfalls": ["Assuming threads help CPU-bound work"],
        }
    )
