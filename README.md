# Sprint Retrospective Web Application

A lightweight retrospective tool inspired by Reetro with the following core capabilities:

- Team and user management with role assignment (Admin, Team Member, Read Only, Guest)
- Retrospective boards with feedback categories (Continue, Stop, Start)
- Voting (up/down) on feedback
- Action tracker sourced from board feedback
- Analytics report covering meeting summary, org insight, and action tracker insight

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5000`.
