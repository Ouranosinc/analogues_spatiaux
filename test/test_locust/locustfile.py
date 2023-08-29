# test app with Locust -- see https://locust.readthedocs.io/en/latest/

from locust import HttpUser, task

class RequestOnlyUser(HttpUser):
  host = "https://app-spatial-analogs-staging.climatedata.ca"
  
  @task
  def goto(self):
    self.client.get("/analogs/Dashboard")

