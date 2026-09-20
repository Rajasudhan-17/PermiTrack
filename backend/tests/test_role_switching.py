from leave_app.models import Role, User

def test_role_switching_authorization(client, seed_data):
    faculty = seed_data["faculty"]

    # 1. Login as faculty
    res = client.post(
        "/login",
        data={"username": faculty.username, "password": "password"}
    )
    assert res.status_code == 302

    # 2. Assert initial role is FACULTY
    res_dash = client.get("/")
    assert res_dash.status_code == 200
    assert f"Welcome, {faculty.full_name or faculty.username}" in res_dash.text
    assert "Role: <span class=\"badge bg-primary\">FACULTY</span>" in res_dash.text

    # 3. Switch role to MENTOR
    res_switch = client.post(
        "/switch-role",
        data={"role": "mentor"}
    )
    assert res_switch.status_code == 302

    # 4. Assert role is now MENTOR in the template rendering
    res_dash_after = client.get("/")
    assert res_dash_after.status_code == 200
    assert "Role: <span class=\"badge bg-primary\">MENTOR</span>" in res_dash_after.text

    # 5. Switch back to FACULTY
    res_switch_back = client.post(
        "/switch-role",
        data={"role": "faculty"}
    )
    assert res_switch_back.status_code == 302

    res_dash_final = client.get("/")
    assert "Role: <span class=\"badge bg-primary\">FACULTY</span>" in res_dash_final.text

    # 6. Logout and verify active role is cleared
    res_logout = client.post("/logout")
    assert res_logout.status_code == 302

    # Login again and verify role resets to FACULTY (original)
    res_login_again = client.post(
        "/login",
        data={"username": faculty.username, "password": "password"}
    )
    assert res_login_again.status_code == 302

    res_dash_login_again = client.get("/")
    assert "Role: <span class=\"badge bg-primary\">FACULTY</span>" in res_dash_login_again.text

    # 7. Logout to clean up
    client.post("/logout")


def test_invalid_role_switching(client, seed_data):
    student = seed_data["student"]

    # 1. Login as student
    res = client.post(
        "/login",
        data={"username": student.username, "password": "password"}
    )
    assert res.status_code == 302

    # 2. Attempt to switch role (should fail because student is not faculty/mentor)
    res_switch = client.post(
        "/switch-role",
        data={"role": "mentor"}
    )
    assert res_switch.status_code == 302

    # 3. Verify student role has not changed
    res_dash = client.get("/")
    assert "Role: <span class=\"badge bg-primary\">STUDENT</span>" in res_dash.text

    # 4. Try to switch to an invalid role value (e.g. 'admin')
    res_switch_invalid = client.post(
        "/switch-role",
        data={"role": "admin"}
    )
    assert res_switch_invalid.status_code == 302

    res_dash_invalid = client.get("/")
    assert "Role: <span class=\"badge bg-primary\">STUDENT</span>" in res_dash_invalid.text
