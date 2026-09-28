import app as healthatlas_app

COUNTRY_ROWS = [{
    "country_id":"AUS","country_name":"Australia","region_id":"WPR",
    "region_name":"Western Pacific","economy_id":"1","economic_phase":"High income",
    "latest_vaccination_year":2024,"avg_coverage":94.5,"total_doses":1000,
    "latest_infection_year":2024,"total_cases":12,
    "latest_population_year":2024,"population":27000000,
}]
REGION_ROWS = [{"region_id":"WPR","region_name":"Western Pacific"}]

class FakeMappings:
    def __init__(self, rows): self.rows = rows
    def all(self): return self.rows

class FakeResult:
    def __init__(self, rows): self.rows = rows
    def mappings(self): return FakeMappings(self.rows)

class FakeConnection:
    def execute(self, statement, params=None):
        sql = str(statement)
        if "SELECT DISTINCT" in sql and "region_id" in sql:
            return FakeResult(REGION_ROWS)
        return FakeResult(COUNTRY_ROWS)
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): return False

class FakeEngine:
    def connect(self): return FakeConnection()

def test_countries_directory_renders(monkeypatch):
    monkeypatch.setattr(healthatlas_app, "POSTGRES_ENGINE", FakeEngine())
    with healthatlas_app.app.test_client() as client:
        response = client.get("/countries")
    assert response.status_code == 200
    assert b"Australia" in response.data
    assert b"PostgreSQL analytics" in response.data

def test_countries_directory_accepts_filters(monkeypatch):
    monkeypatch.setattr(healthatlas_app, "POSTGRES_ENGINE", FakeEngine())
    with healthatlas_app.app.test_client() as client:
        response = client.get("/countries?q=Aus&region=WPR&sort=coverage")
    assert response.status_code == 200
    assert b"Aus" in response.data
    assert b"Western Pacific" in response.data
