"""Real password login and four-role writes on guarded disposable PostgreSQL 16."""
import asyncio
import uuid
from datetime import date, timedelta
import httpx
from sqlalchemy import insert, update
from app.config import settings
from app.main import app
from app.security.password import hash_password
from tests import test_stage3_detection as fixtures


def test_four_role_frontend_flows_real_login_and_postgres():
    old_urls = settings.DATABASE_URL, settings.DATABASE_URL_SYNC
    fixtures.DetectionTests.setUpClass()
    fixture = fixtures.DetectionTests(methodName="runTest")
    try:
        fixture.setUp()
        fixture.test_real_artifact_high_progression()
        usernames = {}
        with fixture.engine.begin() as connection:
            for role in ("PERSONNEL", "COMMANDER", "WELFARE_OFFICER", "ADMIN"):
                identifier = fixture.admin if role == "ADMIN" else uuid.uuid4()
                usernames[role] = str(identifier)
                values = dict(username=str(identifier), password_hash=hash_password("Disposable-password-26186"),
                    role=role, is_active=True, unit_id=fixture.unit if role != "ADMIN" else None,
                    personnel_id=fixture.people[0] if role == "PERSONNEL" else None)
                if role == "ADMIN":
                    connection.execute(update(fixtures.TABLES["users"]).where(fixtures.TABLES["users"].c.id==identifier).values(**values))
                else:
                    connection.execute(insert(fixtures.TABLES["users"]).values(id=identifier, **values))

        async def proof():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                tokens = {}
                for role, username in usernames.items():
                    client.cookies.clear()
                    response = await client.post("/api/v1/auth/login", json={"username":username,"password":"Disposable-password-26186"})
                    assert response.status_code == 200, response.text
                    tokens[role] = response.json()["access_token"]
                client.cookies.clear()
                legacy_role = await client.post("/api/v1/auth/login", json={
                    "username": "auditor_demo", "password": "not-a-valid-test-credential",
                })
                assert legacy_role.status_code in (401, 403)

                async def call(role, method, path, body=None, key=None, expected=200):
                    headers = {"Authorization":"Bearer " + tokens[role]}
                    if key:
                        headers["Idempotency-Key"] = key
                    response = await client.request(method, "/api/v1"+path, json=body, headers=headers)
                    assert response.status_code == expected, (role, method, path, response.text)
                    return response.json()

                for path in ("/auth/me", "/personnel/me", "/personnel/me/risk", "/personnel/me/duties",
                             "/personnel/me/rest", "/personnel/me/leave", "/personnel/support-requests", "/notifications"):
                    await call("PERSONNEL", "GET", path)
                own_risk = await call("PERSONNEL", "GET", "/personnel/me/risk")
                assert set(own_risk) == {"wsi", "baseline", "trend", "peer"}
                assert all(isinstance(signal["status"], str) and signal["status"] for signal in own_risk.values())
                if own_risk["wsi"]["status"] != "VALID":
                    assert own_risk["wsi"]["value"] is None
                await call("PERSONNEL", "GET", "/commander/overview", expected=403)
                for path in ("/commander/overview", "/commander/priority-list?limit=2",
                             "/operational/attention?cutoff=2026-03-16", "/commander/scenarios"):
                    await call("COMMANDER", "GET", path)
                await call("COMMANDER", "GET", "/personnel/self-checks", expected=403)
                alerts = await call("COMMANDER", "GET", "/alerts")
                assert len(alerts["items"]) == 5
                alert = alerts["items"][0]
                ack = await call("COMMANDER", "POST", "/alerts/"+alert["id"]+"/acknowledge",
                    {"expected_revision":alert["revision"],"reason_code":"REVIEWED"}, "e2e-alert-ack")
                resolved = await call("COMMANDER", "POST", "/alerts/"+alert["id"]+"/resolve",
                    {"expected_revision":ack["revision"],"reason_code":"REVIEW_COMPLETE"}, "e2e-alert-resolve")
                assert resolved["status"] == "RESOLVED"

                identities = await call("WELFARE_OFFICER", "POST", "/welfare/personnel/search",
                    {"field":"service_code", "query":str(fixture.people[0]), "purpose_reason":"Requested welfare follow-up"})
                assert identities["items"][0]["id"] == str(fixture.people[0])
                case = await call("WELFARE_OFFICER", "POST", "/welfare/cases", {
                    "personnel_id":str(fixture.people[0]), "request_type":"LEAVE_ASSISTANCE",
                    "personnel_visible_reason":"Discuss requested leave assistance"}, "e2e-case-open")
                case_path = "/welfare/cases/"+case["id"]
                await call("WELFARE_OFFICER", "GET", "/welfare/cases?assigned_to_me=true&limit=2")
                await call("WELFARE_OFFICER", "GET", case_path)
                await call("WELFARE_OFFICER", "POST", case_path+"/actions", {
                    "action_type":"DISCUSSION", "note":"Officer private note", "case_status":"IN_PROGRESS"}, "e2e-case-discussion")
                await call("WELFARE_OFFICER", "POST", case_path+"/actions", {
                    "action_type":"FOLLOW_UP", "note":"Agreed follow-up", "visibility":"PERSONNEL",
                    "follow_up_date":str(date.today()+timedelta(days=2))}, "e2e-case-follow-up")
                await call("WELFARE_OFFICER", "POST", case_path+"/actions", {
                    "action_type":"CLOSE", "note":"Support discussion completed", "visibility":"PERSONNEL"}, "e2e-case-close")
                own_actions = await call("PERSONNEL", "GET", "/personnel/support-requests/"+case["id"]+"/actions")
                assert "Officer private note" not in str(own_actions)
                assert await call("PERSONNEL", "GET", "/notifications")
                await call("COMMANDER", "GET", case_path, expected=403)

                source = {"dataset_type":"training", "source_timestamp":"2026-01-03T00:00:00Z",
                    "csv_data":"personnel_id,training_name,start_date,end_date,hours,status\n"+
                    f"{fixture.people[0]},Disposable training,2026-01-01,2026-01-02,8,COMPLETED\n"}
                validation = await call("ADMIN", "POST", "/admin/imports/validate", source)
                assert validation["status"] == "VALIDATED"
                body = {**source, "checksum":validation["checksum"], "expected_revision":validation["revision"]}
                path = "/admin/imports/"+validation["id"]+"/commit"
                result = await call("ADMIN", "POST", path, body, "e2e-import-commit")
                assert result == await call("ADMIN", "POST", path, body, "e2e-import-commit")
                for path in ("/admin/imports", "/admin/jobs", "/admin/models", "/admin/imports/templates", "/admin/users?role=COMMANDER"):
                    await call("ADMIN", "GET", path)
                health = await call("ADMIN", "GET", "/admin/health")
                assert "table_record_counts" in health
                code = str(uuid.uuid4())
                unit = await call("ADMIN", "POST", "/admin/units", {"unit_code":code,"unit_name":"Disposable unit",
                    "unit_type":"TEST", "sanctioned_strength":5}, "e2e-unit-create", expected=201)
                await call("ADMIN", "PATCH", "/admin/units/"+unit["id"], {
                    "expected_revision":unit["revision"],"unit_name":"Updated disposable unit"})
                person = await call("ADMIN", "POST", "/admin/personnel", {"personnel_code":code,"pseudo_id":code,
                    "full_name":"Disposable master", "unit_id":unit["id"],"rank_or_grade":"TEST","role_title":"TEST"},
                    "e2e-person-create", expected=201)
                await call("ADMIN", "GET", "/admin/personnel/"+person["id"])
                searched = await call("ADMIN", "GET", "/admin/personnel?query=Disposable&unit_id="+unit["id"])
                assert len(searched) == 1

        asyncio.run(proof())
    finally:
        from app.db import session as db_session
        asyncio.run(db_session.engine.dispose())
        fixtures.DetectionTests.tearDownClass()
        settings.DATABASE_URL, settings.DATABASE_URL_SYNC = old_urls
        fixture.engine.dispose()
