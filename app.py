from __future__ import annotations

from datetime import datetime
from enum import Enum

from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///retro.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Role(str, Enum):
    ADMIN = "Admin"
    MEMBER = "Team Member"
    READ_ONLY = "Read Only"
    GUEST = "Guest"


team_members = db.Table(
    "team_members",
    db.Column("team_id", db.Integer, db.ForeignKey("team.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
)


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    members = db.relationship("User", secondary=team_members, backref="teams")


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), nullable=False, unique=True)
    role = db.Column(db.String(32), nullable=False, default=Role.MEMBER.value)


class Board(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    feedback = db.relationship("Feedback", backref="board", cascade="all, delete-orphan")


class FeedbackType(str, Enum):
    CONTINUE = "Continue"
    STOP = "Stop"
    START = "Start"


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    board_id = db.Column(db.Integer, db.ForeignKey("board.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    type = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    votes = db.relationship("Vote", backref="feedback", cascade="all, delete-orphan")
    action_items = db.relationship("ActionItem", backref="feedback", cascade="all, delete-orphan")


class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    feedback_id = db.Column(db.Integer, db.ForeignKey("feedback.id"), nullable=False)
    value = db.Column(db.Integer, nullable=False)  # +1 or -1


class ActionStatus(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    DONE = "Done"


class ActionItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    feedback_id = db.Column(db.Integer, db.ForeignKey("feedback.id"), nullable=False)
    board_id = db.Column(db.Integer, db.ForeignKey("board.id"), nullable=False)
    description = db.Column(db.Text, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    status = db.Column(db.String(32), nullable=False, default=ActionStatus.OPEN.value)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


@app.route("/")
def index():
    return render_template("index.html")


def parse_json(required: list[str]):
    payload = request.get_json(silent=True) or {}
    missing = [f for f in required if not payload.get(f)]
    if missing:
        return None, jsonify({"error": f"Missing required field(s): {', '.join(missing)}"}), 400
    return payload, None, None


@app.route("/api/users", methods=["GET", "POST"])
def users():
    if request.method == "POST":
        payload, err, code = parse_json(["name", "email", "role"])
        if err:
            return err, code
        if payload["role"] not in [r.value for r in Role]:
            return jsonify({"error": "Invalid role"}), 400
        user = User(name=payload["name"], email=payload["email"], role=payload["role"])
        db.session.add(user)
        db.session.commit()
        return jsonify({"id": user.id}), 201

    data = [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "teams": [{"id": t.id, "name": t.name} for t in u.teams],
        }
        for u in User.query.order_by(User.name.asc()).all()
    ]
    return jsonify(data)


@app.route("/api/users/<int:user_id>", methods=["PUT"])
def update_user(user_id: int):
    user = User.query.get_or_404(user_id)
    payload = request.get_json(silent=True) or {}
    if "name" in payload:
        user.name = payload["name"]
    if "email" in payload:
        user.email = payload["email"]
    if "role" in payload:
        if payload["role"] not in [r.value for r in Role]:
            return jsonify({"error": "Invalid role"}), 400
        user.role = payload["role"]
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/teams", methods=["GET", "POST"])
def teams():
    if request.method == "POST":
        payload, err, code = parse_json(["name"])
        if err:
            return err, code
        team = Team(name=payload["name"])
        db.session.add(team)
        db.session.commit()
        return jsonify({"id": team.id}), 201

    data = [
        {
            "id": t.id,
            "name": t.name,
            "members": [
                {"id": u.id, "name": u.name, "email": u.email, "role": u.role}
                for u in sorted(t.members, key=lambda x: x.name.lower())
            ],
        }
        for t in Team.query.order_by(Team.name.asc()).all()
    ]
    return jsonify(data)


@app.route("/api/teams/<int:team_id>/members", methods=["POST"])
def assign_member(team_id: int):
    team = Team.query.get_or_404(team_id)
    payload, err, code = parse_json(["user_id"])
    if err:
        return err, code
    user = User.query.get_or_404(payload["user_id"])
    if user not in team.members:
        team.members.append(user)
        db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/boards", methods=["GET", "POST"])
def boards():
    if request.method == "POST":
        payload, err, code = parse_json(["title"])
        if err:
            return err, code
        board = Board(title=payload["title"])
        db.session.add(board)
        db.session.commit()
        return jsonify({"id": board.id}), 201

    data = [
        {"id": b.id, "title": b.title, "created_at": b.created_at.isoformat()}
        for b in Board.query.order_by(Board.created_at.desc()).all()
    ]
    return jsonify(data)


@app.route("/api/boards/<int:board_id>/feedback", methods=["GET", "POST"])
def board_feedback(board_id: int):
    Board.query.get_or_404(board_id)
    if request.method == "POST":
        payload, err, code = parse_json(["type", "content"])
        if err:
            return err, code
        if payload["type"] not in [t.value for t in FeedbackType]:
            return jsonify({"error": "Invalid feedback type"}), 400
        item = Feedback(
            board_id=board_id,
            author_id=payload.get("author_id"),
            type=payload["type"],
            content=payload["content"],
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({"id": item.id}), 201

    rows = (
        db.session.query(Feedback, func.coalesce(func.sum(Vote.value), 0).label("score"))
        .outerjoin(Vote, Vote.feedback_id == Feedback.id)
        .filter(Feedback.board_id == board_id)
        .group_by(Feedback.id)
        .order_by(Feedback.created_at.desc())
        .all()
    )
    return jsonify(
        [
            {
                "id": fb.id,
                "board_id": fb.board_id,
                "type": fb.type,
                "content": fb.content,
                "author_id": fb.author_id,
                "created_at": fb.created_at.isoformat(),
                "score": score,
            }
            for fb, score in rows
        ]
    )


@app.route("/api/feedback/<int:feedback_id>/vote", methods=["POST"])
def vote_feedback(feedback_id: int):
    Feedback.query.get_or_404(feedback_id)
    payload, err, code = parse_json(["value"])
    if err:
        return err, code
    if payload["value"] not in (-1, 1):
        return jsonify({"error": "Vote must be -1 or +1"}), 400
    vote = Vote(feedback_id=feedback_id, value=payload["value"])
    db.session.add(vote)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/action-items", methods=["GET", "POST"])
def action_items():
    if request.method == "POST":
        payload, err, code = parse_json(["feedback_id", "description"])
        if err:
            return err, code
        fb = Feedback.query.get_or_404(payload["feedback_id"])
        action = ActionItem(
            feedback_id=fb.id,
            board_id=fb.board_id,
            description=payload["description"],
            owner_id=payload.get("owner_id"),
            status=payload.get("status", ActionStatus.OPEN.value),
        )
        db.session.add(action)
        db.session.commit()
        return jsonify({"id": action.id}), 201

    rows = (
        db.session.query(ActionItem, Feedback.content, Board.title)
        .join(Feedback, Feedback.id == ActionItem.feedback_id)
        .join(Board, Board.id == ActionItem.board_id)
        .order_by(ActionItem.created_at.desc())
        .all()
    )
    return jsonify(
        [
            {
                "id": a.id,
                "feedback_id": a.feedback_id,
                "board_id": a.board_id,
                "board_title": board_title,
                "description": a.description,
                "status": a.status,
                "owner_id": a.owner_id,
                "source_feedback": fb_content,
                "created_at": a.created_at.isoformat(),
            }
            for a, fb_content, board_title in rows
        ]
    )


@app.route("/api/reports/summary")
def report_summary():
    feedback_counts = {
        t.value: db.session.query(Feedback).filter(Feedback.type == t.value).count()
        for t in FeedbackType
    }
    status_counts = {
        s.value: db.session.query(ActionItem).filter(ActionItem.status == s.value).count()
        for s in ActionStatus
    }

    org_insight = {
        "boards": Board.query.count(),
        "feedback": Feedback.query.count(),
        "members": User.query.count(),
        "teams": Team.query.count(),
    }

    action_insight = {
        "total_actions": ActionItem.query.count(),
        "status_breakdown": status_counts,
    }

    meeting_summary = {
        "feedback_breakdown": feedback_counts,
        "top_feedback": [
            {
                "id": fb_id,
                "content": content,
                "score": score,
                "type": fb_type,
            }
            for fb_id, content, score, fb_type in (
                db.session.query(
                    Feedback.id,
                    Feedback.content,
                    func.coalesce(func.sum(Vote.value), 0).label("score"),
                    Feedback.type,
                )
                .outerjoin(Vote, Vote.feedback_id == Feedback.id)
                .group_by(Feedback.id)
                .order_by(func.coalesce(func.sum(Vote.value), 0).desc())
                .limit(5)
                .all()
            )
        ],
    }

    return jsonify(
        {
            "meeting_summary": meeting_summary,
            "organization_insight": org_insight,
            "action_tracker_insight": action_insight,
        }
    )


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
