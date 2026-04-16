const jsonHeaders = { "Content-Type": "application/json" };

async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.error || `Request failed: ${res.status}`);
  }
  return res.json();
}

function option(id, label) {
  const opt = document.createElement("option");
  opt.value = id;
  opt.textContent = label;
  return opt;
}

async function refreshUsers() {
  const users = await api("/api/users");
  const list = document.getElementById("users-list");
  const assignUser = document.getElementById("assign-user");
  list.innerHTML = "";
  assignUser.innerHTML = "";

  users.forEach((u) => {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${u.name}</strong> (${u.role})<div class="small">${u.email}</div>`;
    list.appendChild(li);
    assignUser.appendChild(option(u.id, `${u.name} (${u.role})`));
  });
}

async function refreshTeams() {
  const teams = await api("/api/teams");
  const assignTeam = document.getElementById("assign-team");
  assignTeam.innerHTML = "";
  teams.forEach((t) => assignTeam.appendChild(option(t.id, t.name)));
}

async function refreshBoards() {
  const boards = await api("/api/boards");
  const list = document.getElementById("boards-list");
  const fbBoard = document.getElementById("feedback-board");
  list.innerHTML = "";
  fbBoard.innerHTML = "";

  boards.forEach((b) => {
    const li = document.createElement("li");
    li.textContent = `${b.title} (${new Date(b.created_at).toLocaleString()})`;
    list.appendChild(li);
    fbBoard.appendChild(option(b.id, b.title));
  });

  if (boards[0]) {
    await refreshFeedback(boards[0].id);
  }
}

async function refreshFeedback(boardId) {
  if (!boardId) return;
  const rows = await api(`/api/boards/${boardId}/feedback`);
  const list = document.getElementById("feedback-list");
  const actionFeedback = document.getElementById("action-feedback");
  list.innerHTML = "";
  actionFeedback.innerHTML = "";

  rows.forEach((r) => {
    const li = document.createElement("li");
    li.innerHTML = `<strong>[${r.type}]</strong> ${r.content}
      <div class="small">Score: ${r.score}</div>`;
    const up = document.createElement("button");
    up.textContent = "▲";
    up.onclick = async () => {
      await api(`/api/feedback/${r.id}/vote`, {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({ value: 1 }),
      });
      await refreshFeedback(boardId);
    };

    const down = document.createElement("button");
    down.textContent = "▼";
    down.onclick = async () => {
      await api(`/api/feedback/${r.id}/vote`, {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({ value: -1 }),
      });
      await refreshFeedback(boardId);
    };

    li.appendChild(up);
    li.appendChild(down);
    list.appendChild(li);
    actionFeedback.appendChild(option(r.id, `[${r.type}] ${r.content.slice(0, 40)}`));
  });
}

async function refreshActions() {
  const rows = await api("/api/action-items");
  const list = document.getElementById("actions-list");
  list.innerHTML = "";
  rows.forEach((a) => {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${a.description}</strong><div class="small">Board: ${a.board_title} • Status: ${a.status}</div>`;
    list.appendChild(li);
  });
}

async function refreshReports() {
  const report = await api("/api/reports/summary");
  document.getElementById("report-output").textContent = JSON.stringify(report, null, 2);
}

function bindForms() {
  document.getElementById("create-user-form").onsubmit = async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target).entries());
    await api("/api/users", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(data),
    });
    e.target.reset();
    await refreshUsers();
  };

  document.getElementById("create-team-form").onsubmit = async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target).entries());
    await api("/api/teams", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(data),
    });
    e.target.reset();
    await refreshTeams();
  };

  document.getElementById("assign-team-form").onsubmit = async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target).entries());
    await api(`/api/teams/${data.team_id}/members`, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ user_id: Number(data.user_id) }),
    });
    await refreshUsers();
    await refreshTeams();
  };

  document.getElementById("create-board-form").onsubmit = async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target).entries());
    await api("/api/boards", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(data),
    });
    e.target.reset();
    await refreshBoards();
  };

  document.getElementById("feedback-form").onsubmit = async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target).entries());
    await api(`/api/boards/${data.board_id}/feedback`, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ type: data.type, content: data.content }),
    });
    e.target.reset();
    await refreshBoards();
    await refreshActions();
  };

  document.getElementById("action-form").onsubmit = async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target).entries());
    await api("/api/action-items", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ feedback_id: Number(data.feedback_id), description: data.description }),
    });
    e.target.reset();
    await refreshActions();
    await refreshReports();
  };

  document.getElementById("feedback-board").onchange = async (e) => {
    await refreshFeedback(e.target.value);
  };

  document.getElementById("refresh-reports").onclick = refreshReports;
}

(async function init() {
  bindForms();
  await refreshUsers();
  await refreshTeams();
  await refreshBoards();
  await refreshActions();
  await refreshReports();
})();
