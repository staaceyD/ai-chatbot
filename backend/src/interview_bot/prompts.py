from interview_bot.domain import Difficulty, Question, Topic

TOPIC_LABELS = {
    Topic.PYTHON: "Python",
    Topic.JAVASCRIPT: "JavaScript",
    Topic.TYPESCRIPT: "TypeScript",
    Topic.REACT: "React",
    Topic.SYSTEM_DESIGN: "system design",
    Topic.DATABASES: "databases and SQL",
    Topic.ALGORITHMS: "algorithms",
    Topic.DATA_STRUCTURES: "data structures",
    Topic.CONCURRENCY: "concurrency",
    Topic.NETWORKING: "networking and HTTP",
    Topic.API_DESIGN: "API design",
    Topic.SECURITY: "application security",
    Topic.TESTING: "testing",
    Topic.OPERATING_SYSTEMS: "operating systems",
    Topic.DEVOPS: "DevOps and deployment",
}

# What counts as being "about" a topic. Without this the model drifts towards
# questions that would read the same way whatever the topic was.
TOPIC_SCOPES = {
    Topic.PYTHON: "its syntax, semantics, standard library, tooling or ecosystem",
    Topic.JAVASCRIPT: "its syntax, semantics, runtime model, standard library or ecosystem",
    Topic.TYPESCRIPT: "its type system, inference, compiler behaviour, tooling or ecosystem",
    Topic.REACT: "its rendering model, hooks, component API, tooling or ecosystem",
    Topic.SYSTEM_DESIGN: (
        "how to split, scale, cache, queue and fail over the parts of a system, "
        "and the trade-offs between those choices"
    ),
    Topic.DATABASES: (
        "the relational model, SQL semantics, indexing, query planning, transactions and "
        "isolation levels, schema design, replication, or where a non-relational store fits"
    ),
    Topic.ALGORITHMS: (
        "how a named algorithm works, what it costs in time and space, and when to reach "
        "for it instead of another"
    ),
    Topic.DATA_STRUCTURES: (
        "how a named structure is laid out in memory, what each of its operations costs, "
        "and which structure suits a given access pattern"
    ),
    Topic.CONCURRENCY: (
        "threads, processes, async scheduling, locks and other coordination primitives, "
        "and the races, deadlocks and starvation they cause"
    ),
    Topic.NETWORKING: (
        "TCP, TLS and DNS, HTTP semantics and status codes, caching headers, and what "
        "actually crosses the wire during a request"
    ),
    Topic.API_DESIGN: (
        "resource modelling, versioning, idempotency, pagination, error contracts, and "
        "the differences between REST, RPC and GraphQL styles"
    ),
    Topic.SECURITY: (
        "authentication and authorization, common web vulnerabilities and their fixes, "
        "secret and credential handling, and threat modelling"
    ),
    Topic.TESTING: (
        "what to test at which level, test doubles, flaky and slow tests, coverage as a "
        "signal, and how testability shapes a design"
    ),
    Topic.OPERATING_SYSTEMS: (
        "processes and threads, virtual memory and paging, scheduling, file systems, "
        "and system calls"
    ),
    Topic.DEVOPS: (
        "build and release pipelines, containers, infrastructure as code, deployment and "
        "rollback strategies, and observability in production"
    ),
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

EXPLAIN_SYSTEM = (
    "You are a patient senior engineer teaching the answer to an interview question, "
    "so the reader does not have to look anything up. "
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
        f"Ask one interview question about {TOPIC_LABELS[topic]}, suitable for "
        f"{DIFFICULTY_LABELS[difficulty]}."
        f"\n\nThe question must stay inside the scope of {TOPIC_LABELS[topic]}: "
        f"{TOPIC_SCOPES[topic]}. A question that would read the same way for any other "
        "topic is not acceptable."
        "\n\nThe question must be answerable in a few sentences of prose, at most "
        "alongside a one-line snippet — a single statement, expression, query or command — "
        "where the exact syntax is the point. Never ask the candidate to implement a "
        "function, a class or an algorithm: this is a spoken conversation, not a coding "
        "exercise."
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
        "Judge the substance, not the wording or length: a correct one-line snippet "
        "covers a key point as fully as a sentence of prose would. "
        "If the answer is off topic or empty, score it 0."
        "\n\nWrite the verdict as one or two sentences addressed to the candidate. "
        "List the key points they covered and the ones they missed."
        "\n\nRespond with JSON shaped exactly like: "
        '{"score": 3, "verdict": "...", "covered": ["..."], "missed": ["..."]}'
    )


def explain_prompt(*, question: Question) -> str:
    key_points = "\n".join(f"- {point}" for point in question.key_points)
    return (
        f"Question asked:\n{question.prompt}"
        f"\n\nKey points a complete answer covers:\n{key_points}"
        f"\n\nTeach the answer to {DIFFICULTY_LABELS[question.difficulty]}."
        "\n\nWrite the answer out in full, as a good textbook would: three or four short "
        "paragraphs separated by blank lines. Say why each key point matters rather than only "
        "that it does, and ground it in a concrete example drawn from "
        f"{TOPIC_LABELS[question.topic]}."
        "\n\nWhere one line of code makes a point faster than a sentence, show it in a "
        "fenced block. Keep such a block to a line or two — never write out a whole "
        "function or algorithm."
        "\n\nThen expand every key point into one or two sentences of its own, and list the "
        "mistakes engineers commonly make about this topic."
        "\n\nRespond with JSON shaped exactly like: "
        '{"answer": "...", "points": [{"point": "...", "detail": "..."}], "pitfalls": ["..."]}'
    )
