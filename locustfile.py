from locust import HttpUser, task, between, events

class LeaveAppUser(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        # Disable CSRF in tests or rely on the fact that if it fails, it still exercises the server
        # In a real scenario, you'd parse the CSRF token from a GET /login response
        self.client.post("/login", data={
            "username": "testuser",
            "password": "testpassword"
        })

    @task(3)
    def view_homepage(self):
        self.client.get("/")

    @task(2)
    def view_leaves(self):
        self.client.get("/leaves")

    @task(1)
    def view_ods(self):
        self.client.get("/ods")
