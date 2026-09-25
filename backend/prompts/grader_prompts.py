GRADER_SYSTEM_PROMPT = """You are grading whether a retrieved document is relevant to an ACTUS financial contract question.
Respond ONLY with JSON: {"binary_score": "yes"} or {"binary_score": "no"}"""

GRADER_USER_TEMPLATE = """Question: {query}

Document:
{document}

Is this document relevant?"""

ANSWER_GRADER_SYSTEM_PROMPT = """You are checking if an AI answer actually resolves the user's ACTUS question.
Respond ONLY with JSON: {"binary_score": "yes"} or {"binary_score": "no"}"""

ANSWER_GRADER_USER_TEMPLATE = """Question: {query}
Answer: {answer}

Does this answer resolve the question?"""
