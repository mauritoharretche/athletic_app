from datetime import date, timedelta

from fastapi.testclient import TestClient


def register_user(client: TestClient, name: str, email: str, role: str, password: str = "password123"):
    response = client.post(
        "/auth/register",
        json={"name": name, "email": email, "role": role, "password": password},
    )
    assert response.status_code == 201, response.text
    return response.json()


def login(client: TestClient, email: str, password: str = "password123") -> str:
    response = client.post(
        "/auth/login",
        params={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_plan_for_tests(
    client: TestClient,
    coach_token: str,
    athlete_id: int,
    start: date,
    sessions: list[dict] | None = None,
) -> dict:
    payload = {
        "athlete_id": athlete_id,
        "name": "10K Base",
        "goal_type": "10K",
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=30)).isoformat(),
        "notes": "Fase base",
        "sessions": sessions
        or [
            {
                "date": start.isoformat(),
                "type": "RODAJE",
                "title": "Easy Run",
                "description": "30 minutos Z2",
                "planned_distance": 6.0,
                "planned_duration": 30,
                "planned_rpe": 4,
                "notes_for_athlete": "Respirar nasal",
            },
            {
                "date": (start + timedelta(days=2)).isoformat(),
                "type": "PASADAS",
                "title": "8x400",
                "planned_distance": 10.0,
                "planned_duration": 60,
                "planned_rpe": 7,
            },
        ],
    }

    response = client.post(
        "/plans",
        json=payload,
        headers=auth_header(coach_token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_coach_creates_plan_and_athlete_reads_it(client: TestClient):
    athlete = register_user(client, "Athlete One", "athlete@example.com", "ATHLETE")
    register_user(client, "Coach One", "coach@example.com", "COACH")

    athlete_token = login(client, "athlete@example.com")
    coach_token = login(client, "coach@example.com")

    start = date(2024, 3, 11)
    plan_data = create_plan_for_tests(client, coach_token, athlete["id"], start)
    assert plan_data["name"] == "10K Base"
    assert len(plan_data["sessions"]) == 2

    list_response = client.get(
        f"/plans/athlete/{athlete['id']}",
        headers=auth_header(athlete_token),
    )
    assert list_response.status_code == 200, list_response.text
    plans = list_response.json()
    assert len(plans) == 1
    assert plans[0]["id"] == plan_data["id"]
    assert plans[0]["sessions"][0]["title"] == "Easy Run"


def test_refresh_and_invite_flow(client: TestClient):
    athlete = register_user(client, "Invitee", "invitee@example.com", "ATHLETE")
    coach = register_user(client, "Inviter", "inviter@example.com", "COACH")

    athlete_token = login(client, "invitee@example.com")
    coach_token = login(client, "inviter@example.com")

    refresh_resp = client.post("/auth/refresh", headers=auth_header(athlete_token))
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()

    invite_resp = client.post(
        "/auth/invite-athlete",
        json={"athlete_email": athlete["email"]},
        headers=auth_header(coach_token),
    )
    assert invite_resp.status_code == 200
    invite_again = client.post(
        "/auth/invite-athlete",
        json={"athlete_email": athlete["email"]},
        headers=auth_header(coach_token),
    )
    assert invite_again.status_code == 200

    forbidden_invite = client.post(
        "/auth/invite-athlete",
        json={"athlete_email": athlete["email"]},
        headers=auth_header(athlete_token),
    )
    assert forbidden_invite.status_code == 403


def test_athlete_cannot_duplicate_manual_session_same_day(client: TestClient):
    register_user(client, "Runner", "runner@example.com", "ATHLETE")
    token = login(client, "runner@example.com")

    payload = {
        "date": date(2024, 3, 15).isoformat(),
        "actual_distance": 12.5,
        "actual_duration": 65,
        "actual_rpe": 6,
        "surface": "Trail",
        "shoes": "Pegasus",
        "notes": "Great run",
    }
    first = client.post("/sessions/done", json=payload, headers=auth_header(token))
    assert first.status_code == 201, first.text

    duplicate = client.post("/sessions/done", json=payload, headers=auth_header(token))
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "A session for this date already exists."


def test_planned_session_logging_requires_ownership_and_unique(client: TestClient):
    athlete_one = register_user(client, "Athlete 1", "ath1@example.com", "ATHLETE")
    athlete_two = register_user(client, "Athlete 2", "ath2@example.com", "ATHLETE")
    register_user(client, "Coach", "coach@team.com", "COACH")

    token_one = login(client, "ath1@example.com")
    token_two = login(client, "ath2@example.com")
    coach_token = login(client, "coach@team.com")

    plan = create_plan_for_tests(client, coach_token, athlete_one["id"], date(2024, 3, 18))
    planned_session_id = plan["sessions"][0]["id"]

    payload = {
        "date": plan["sessions"][0]["date"],
        "planned_session_id": planned_session_id,
        "actual_distance": 5.0,
        "actual_duration": 30,
    }

    first = client.post("/sessions/done", json=payload, headers=auth_header(token_one))
    assert first.status_code == 201, first.text

    duplicate = client.post("/sessions/done", json=payload, headers=auth_header(token_one))
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "You already logged this planned session."

    forbidden = client.post("/sessions/done", json=payload, headers=auth_header(token_two))
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "Not your session."


def test_coach_dashboard_metrics(client: TestClient):
    athlete_one = register_user(client, "Ana Runner", "ana@example.com", "ATHLETE")
    athlete_two = register_user(client, "Beto Runner", "beto@example.com", "ATHLETE")
    register_user(client, "Coach Dash", "coachdash@example.com", "COACH")

    token_one = login(client, "ana@example.com")
    catchall_token = login(client, "beto@example.com")
    coach_token = login(client, "coachdash@example.com")

    today = date.today()
    plan_sessions = [
        {
            "date": today.isoformat(),
            "type": "RODAJE",
            "title": "Hoy",
            "planned_distance": 8,
        },
        {
            "date": (today - timedelta(days=2)).isoformat(),
            "type": "PASADAS",
            "title": "Series",
            "planned_distance": 6,
        },
    ]
    plan = create_plan_for_tests(
        client, coach_token, athlete_one["id"], today - timedelta(days=3), sessions=plan_sessions
    )

    other_plan = create_plan_for_tests(
        client,
        coach_token,
        athlete_two["id"],
        today - timedelta(days=10),
        sessions=[
            {
                "date": (today - timedelta(days=10)).isoformat(),
                "type": "RODAJE",
                "title": "Old",
                "planned_distance": 5,
            }
        ],
    )
    assert other_plan["athlete_id"] == athlete_two["id"]

    payload = {
        "date": today.isoformat(),
        "planned_session_id": plan["sessions"][0]["id"],
        "actual_distance": 8.5,
        "actual_duration": 42,
    }
    log_resp = client.post("/sessions/done", json=payload, headers=auth_header(token_one))
    assert log_resp.status_code == 201, log_resp.text

    # manual session outside plan for athlete two within week to test zero planned/completed
    manual_payload = {
        "date": today.isoformat(),
        "actual_distance": 5,
        "actual_duration": 35,
    }
    manual_resp = client.post("/sessions/done", json=manual_payload, headers=auth_header(catchall_token))
    assert manual_resp.status_code == 201

    dashboard_resp = client.get("/dashboard/coach/me", headers=auth_header(coach_token))
    assert dashboard_resp.status_code == 200, dashboard_resp.text
    data = dashboard_resp.json()
    assert len(data) == 2
    ana_metrics = next(item for item in data if item["athlete_id"] == athlete_one["id"])
    beto_metrics = next(item for item in data if item["athlete_id"] == athlete_two["id"])

    assert ana_metrics["planned_sessions_week"] == 2
    assert ana_metrics["completed_sessions_week"] == 1
    assert ana_metrics["completed_distance_week"] == 8.5
    assert ana_metrics["compliance_rate"] == 0.5

    assert beto_metrics["planned_sessions_week"] == 0
    assert beto_metrics["completed_sessions_week"] == 1
    assert beto_metrics["compliance_rate"] is None


def test_athlete_updates_and_deletes_session(client: TestClient):
    athlete = register_user(client, "Updater", "update@example.com", "ATHLETE")
    token = login(client, "update@example.com")

    payload = {
        "date": date(2024, 4, 2).isoformat(),
        "actual_distance": 7,
        "actual_duration": 40,
        "actual_rpe": 6,
    }
    response = client.post("/sessions/done", json=payload, headers=auth_header(token))
    assert response.status_code == 201
    session_id = response.json()["id"]

    update_payload = {
        "actual_distance": 10,
        "actual_rpe": 7,
        "notes": "Felt strong",
    }
    update_resp = client.put(
        f"/sessions/done/{session_id}", json=update_payload, headers=auth_header(token)
    )
    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()
    assert updated["actual_distance"] == 10
    assert updated["notes"] == "Felt strong"

    delete_resp = client.delete(f"/sessions/done/{session_id}", headers=auth_header(token))
    assert delete_resp.status_code == 204

    list_resp = client.get("/sessions/done/me", headers=auth_header(token))
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 0


def test_coach_filters_sessions_by_date_range(client: TestClient):
    athlete = register_user(client, "Filter", "filter@example.com", "ATHLETE")
    coach = register_user(client, "CoachFilter", "coachfilter@example.com", "COACH")
    coach_token = login(client, "coachfilter@example.com")
    athlete_token = login(client, "filter@example.com")

    # create link by plan creation
    plan = create_plan_for_tests(client, coach_token, athlete["id"], date(2024, 1, 1))
    payloads = [
        {"date": date(2024, 1, 5).isoformat(), "actual_distance": 5},
        {"date": date(2024, 1, 10).isoformat(), "actual_distance": 8},
        {"date": date(2024, 2, 15).isoformat(), "actual_distance": 12},
    ]
    for payload in payloads:
        resp = client.post("/sessions/done", json=payload, headers=auth_header(athlete_token))
        assert resp.status_code == 201

    filter_resp = client.get(
        f"/sessions/done/athlete/{athlete['id']}",
        headers=auth_header(coach_token),
        params={"start_date": date(2024, 1, 6).isoformat(), "end_date": date(2024, 1, 31).isoformat()},
    )
    assert filter_resp.status_code == 200, filter_resp.text
    data = filter_resp.json()
    assert len(data) == 1
    assert data[0]["actual_distance"] == 8


def test_athlete_history_summary(client: TestClient):
    athlete = register_user(client, "History Runner", "history@example.com", "ATHLETE")
    coach = register_user(client, "History Coach", "historycoach@example.com", "COACH")

    athlete_token = login(client, "history@example.com")
    coach_token = login(client, "historycoach@example.com")

    today = date.today()
    plan = create_plan_for_tests(
        client,
        coach_token,
        athlete["id"],
        today - timedelta(days=1),
        sessions=[
            {
                "date": today.isoformat(),
                "type": "RODAJE",
                "title": "Tempo",
                "planned_distance": 10,
            }
        ],
    )
    planned_session_id = plan["sessions"][0]["id"]

    def log(payload):
        resp = client.post("/sessions/done", json=payload, headers=auth_header(athlete_token))
        assert resp.status_code == 201, resp.text
        return resp.json()

    log(
        {
            "date": today.isoformat(),
            "planned_session_id": planned_session_id,
            "actual_distance": 10,
            "actual_duration": 50,
            "actual_rpe": 7,
        }
    )
    log(
        {
            "date": (today - timedelta(days=2)).isoformat(),
            "actual_distance": 8,
            "actual_duration": 45,
            "actual_rpe": 6,
        }
    )
    log(
        {
            "date": (today - timedelta(days=10)).isoformat(),
            "actual_distance": 5,
            "actual_duration": 30,
            "actual_rpe": 5,
        }
    )
    log(
        {
            "date": (today - timedelta(days=40)).isoformat(),
            "actual_distance": 12,
            "actual_duration": 60,
            "actual_rpe": 6,
        }
    )

    history_resp = client.get(f"/athletes/{athlete['id']}/history", headers=auth_header(athlete_token))
    assert history_resp.status_code == 200, history_resp.text
    data = history_resp.json()
    assert data["week_sessions"] == 2
    assert data["week_total_distance"] == 18.0
    assert data["month_sessions"] == 3
    assert data["month_total_distance"] == 23.0
    assert round(data["week_avg_rpe"], 1) == 6.5
    assert round(data["month_avg_rpe"], 2) == round((7 + 6 + 5) / 3, 2)
    assert data["session_type_distribution"]["RODAJE"] == 1
    assert data["session_type_distribution"]["MANUAL"] == 2

    history_coach = client.get(f"/athletes/{athlete['id']}/history", headers=auth_header(coach_token))
    assert history_coach.status_code == 200
