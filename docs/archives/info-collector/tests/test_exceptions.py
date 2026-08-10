from scripts.lib.exceptions import ArtifactError, GateFailureError, InfoCollectorError


class TestHierarchy:
    def test_info_collector_error_is_exception(self):
        assert issubclass(InfoCollectorError, Exception)

    def test_gate_failure_error_is_info_collector_error(self):
        assert issubclass(GateFailureError, InfoCollectorError)

    def test_artifact_error_is_info_collector_error(self):
        assert issubclass(ArtifactError, InfoCollectorError)

    def test_gate_failure_instance_is_info_collector_error(self):
        assert isinstance(GateFailureError("g", ["b"]), InfoCollectorError)

    def test_artifact_error_instance_is_info_collector_error(self):
        assert isinstance(ArtifactError("/p", "r"), InfoCollectorError)


class TestGateFailureError:
    def test_stores_phase(self):
        e = GateFailureError("scope", ["missing field: goal_type"])
        assert e.phase == "scope"

    def test_stores_blockers(self):
        e = GateFailureError("scope", ["no goal_type", "no audience"])
        assert e.blockers == ["no goal_type", "no audience"]

    def test_empty_blockers(self):
        e = GateFailureError("collect", [])
        assert e.blockers == []

    def test_message_format(self):
        e = GateFailureError("scope", ["no goal_type", "no audience"])
        assert str(e) == "Gate 'scope' blocked: no goal_type; no audience"

    def test_single_blocker_message(self):
        e = GateFailureError("scope", ["no goal_type"])
        assert str(e) == "Gate 'scope' blocked: no goal_type"


class TestArtifactError:
    def test_stores_path(self):
        e = ArtifactError("/tmp/scope.json", "file not found")
        assert e.path == "/tmp/scope.json"

    def test_stores_reason(self):
        e = ArtifactError("/tmp/scope.json", "file not found")
        assert e.reason == "file not found"

    def test_message_format(self):
        e = ArtifactError("/tmp/scope.json", "file not found")
        assert str(e) == "Artifact error at /tmp/scope.json: file not found"
