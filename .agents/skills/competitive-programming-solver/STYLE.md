# Python Style

Default language: Python.

Follow this coding style:

- Output only Python code.
- No Markdown.
- No explanations.
- No analysis.

Do not use:

- if __name__ == "__main__":
- unnecessary main() functions
- unnecessary wrapper functions
- unnecessary helper functions
- unnecessary classes
- unnecessary constants

Prefer:

- input()
- print()

Use sys.stdin.readline() only when genuinely helpful.

Use natural competitive programming variable names such as:

- n
- m
- k
- arr
- nums
- ans
- dp
- pref
- cnt
- adj
- vis
- parent

Keep implementations simple.

If two algorithms have equal complexity, choose the implementation that looks more handwritten.

Avoid AI-looking templates.

Avoid reusable-library style code.

Use at most two short comments.

The code should resemble accepted Codeforces solutions around the 1600–2200 rating level.

Before writing the final solution, simplify it if possible while preserving complexity.
