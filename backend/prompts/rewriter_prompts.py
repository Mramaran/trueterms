REWRITER_SYSTEM_PROMPT = """Rewrite the user query using precise ACTUS terms to improve vector store retrieval.
Use terms like: nominalInterestRate, maturityDate, PAM, ANN, LAM, cycleOfInterestPayment, contractRole, etc.
Return ONLY the rewritten query string."""

REWRITER_USER_TEMPLATE = """Rewrite for better ACTUS retrieval: {query}"""
