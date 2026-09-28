import ensure_cloud_data


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class FakeConnection:
    def __init__(self, value):
        self.value = value

    def execute(self, statement, params=None):
        return FakeScalarResult(self.value)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeEngine:
    def __init__(self, value):
        self.value = value

    def connect(self):
        return FakeConnection(self.value)


def test_analytics_ready_true():
    engine = FakeEngine(
        "analytics.country_health_summary"
    )
    assert ensure_cloud_data.analytics_ready(engine) is True


def test_analytics_ready_false():
    engine = FakeEngine(None)
    assert ensure_cloud_data.analytics_ready(engine) is False
