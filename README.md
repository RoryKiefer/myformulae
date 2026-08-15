# myformulae
### Rory's formula solver repository
Coded in a couple of sessions via Claude Sonnet and Cursor as a thought experiment.

<img width="961" height="1479" alt="Screenshot 2026-08-15 192417" src="https://github.com/user-attachments/assets/2acae9ce-dc54-4635-9a1e-46f486f74099" />

#### Tentpoles:
- Python
- Sanic
- Jinja
- SymPy
- front-end/UI or API
- containerized

#### Focus:
- demonstrating with genAI, SDLC best practices can be followed while meeting tight deadlines
  - see agent markdown in `.cursor/` for best practices
- (the cost of) Mythos/Opus not necessary for making elegant, useful solutions
- use of specifc models and custom agents via Cursor and GitHub integration

#### Execution Instructions:
- python3 -m venv .venv
- .venv/Scripts/pip install -r ./requirements.txt (*use `pip.exe` if OS=Windows*)
- .venv/Scripts/python.exe app.py

#### Initial Claude (Sonnet 5) Prompt:
`Assume the role of a python expert. Using sanic and sympy, design an application that takes an algebraic formula as input, and shows the solution as output. The input should be restricted to a single variable: x. Ask me a series of questions about architectural design decisions to help me arrive at the best solution.`
