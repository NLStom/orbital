"""Tests for PgSessionStorage — sessions and artifacts."""

import uuid


# ── Session tests ────────────────────────────────────────────


class TestCreateSession:
    def test_create_session(self, storage):
        session = storage.create_session(data_source="custom", name="My Session")
        assert session["name"] == "My Session"
        assert session["dataSource"] == "custom"
        assert session["createdBy"]  # non-empty
        assert session["createdAt"]
        assert session["updatedAt"]
        assert session["messages"] == []
        assert session["insights"] == []
        assert session["datasets"] == []
        assert session["memory"] == {
            "facts": [],
            "preferences": [],
            "corrections": [],
            "conclusions": [],
        }
        # id is a valid UUID
        uuid.UUID(session["id"])

    def test_create_session_default_name(self, storage):
        session = storage.create_session(data_source="custom", name="")
        assert session["name"] == "Untitled Session"

        session2 = storage.create_session(data_source="custom", name="   ")
        assert session2["name"] == "Untitled Session"


class TestGetSession:
    def test_get_session(self, storage):
        created = storage.create_session(data_source="custom", name="Test")
        fetched = storage.get_session(created["id"])
        assert fetched is not None
        assert fetched["id"] == created["id"]
        assert fetched["name"] == "Test"
        assert fetched["messages"] == []
        assert fetched["memory"]["facts"] == []

    def test_get_session_not_found(self, storage):
        assert storage.get_session(str(uuid.uuid4())) is None


class TestListSessions:
    def test_list_sessions(self, storage):
        s1 = storage.create_session(data_source="custom", name="First")
        s2 = storage.create_session(data_source="custom", name="Second")
        # Touch s1 so it has a later updatedAt
        storage.update_session(s1["id"], {"name": "First Updated"})

        sessions = storage.list_sessions()
        assert len(sessions) >= 2
        ids = [s["id"] for s in sessions]
        assert s1["id"] in ids
        assert s2["id"] in ids
        # s1 was updated last, should be first
        assert ids.index(s1["id"]) < ids.index(s2["id"])

    def test_list_sessions_empty(self, storage):
        sessions = storage.list_sessions()
        assert sessions == []


class TestUpdateSession:
    def test_update_session_name(self, storage):
        session = storage.create_session(data_source="custom", name="Old")
        updated = storage.update_session(session["id"], {"name": "New"})
        assert updated["name"] == "New"

    def test_update_session_add_message(self, storage):
        session = storage.create_session(data_source="custom", name="Chat")
        updated = storage.update_session(
            session["id"],
            {"addMessage": {"role": "user", "content": "Hello"}},
        )
        assert len(updated["messages"]) == 1
        msg = updated["messages"][0]
        assert msg["role"] == "user"
        assert msg["content"] == "Hello"
        assert "id" in msg
        assert "timestamp" in msg
        uuid.UUID(msg["id"])

    def test_update_session_add_message_with_charts(self, storage):
        session = storage.create_session(data_source="custom", name="Viz")
        charts = [{"type": "bar", "title": "Test"}]
        graphs = [{"nodes": [], "edges": []}]
        tool_calls = [{"tool": "run_sql", "input": {}}]
        updated = storage.update_session(
            session["id"],
            {
                "addMessage": {
                    "role": "assistant",
                    "content": "Here's a chart",
                    "charts": charts,
                    "graphs": graphs,
                    "toolCalls": tool_calls,
                }
            },
        )
        msg = updated["messages"][0]
        assert msg["charts"] == charts
        assert msg["graphs"] == graphs
        assert msg["toolCalls"] == tool_calls

    def test_update_session_add_insight(self, storage):
        session = storage.create_session(data_source="custom", name="Ins")
        updated = storage.update_session(
            session["id"],
            {
                "addInsight": {
                    "title": "Key Finding",
                    "summary": "Something important",
                    "messageId": "msg-1",
                }
            },
        )
        assert len(updated["insights"]) == 1
        ins = updated["insights"][0]
        assert ins["title"] == "Key Finding"
        assert ins["summary"] == "Something important"
        assert "id" in ins
        assert "createdAt" in ins
        uuid.UUID(ins["id"])

    def test_update_session_update_insight(self, storage):
        session = storage.create_session(data_source="custom", name="Up")
        session = storage.update_session(
            session["id"],
            {"addInsight": {"title": "Old Title", "summary": "Old summary"}},
        )
        insight_id = session["insights"][0]["id"]
        updated = storage.update_session(
            session["id"],
            {"updateInsight": {"id": insight_id, "title": "New Title"}},
        )
        assert updated["insights"][0]["title"] == "New Title"
        assert updated["insights"][0]["summary"] == "Old summary"

    def test_update_session_add_dataset(self, storage):
        session = storage.create_session(data_source="custom", name="DS")
        ds_id = str(uuid.uuid4())
        updated = storage.update_session(session["id"], {"addDataset": ds_id})
        assert ds_id in updated["datasets"]
        # Idempotent
        updated2 = storage.update_session(session["id"], {"addDataset": ds_id})
        assert updated2["datasets"].count(ds_id) == 1

    def test_update_session_remove_dataset(self, storage):
        session = storage.create_session(data_source="custom", name="DS")
        ds_id = str(uuid.uuid4())
        storage.update_session(session["id"], {"addDataset": ds_id})
        updated = storage.update_session(session["id"], {"removeDataset": ds_id})
        assert ds_id not in updated["datasets"]

    def test_update_session_memory(self, storage):
        session = storage.create_session(data_source="custom", name="Mem")
        new_memory = {
            "facts": [{"content": "User likes Python", "added_at": "2025-01-01T00:00:00"}],
            "preferences": [],
            "corrections": [],
            "conclusions": [],
        }
        updated = storage.update_session(session["id"], {"memory": new_memory})
        assert updated["memory"] == new_memory

    def test_update_session_history_summary(self, storage):
        session = storage.create_session(data_source="custom", name="Hist")
        updated = storage.update_session(
            session["id"],
            {"historySummary": "A summary of events", "historySummaryUpToIndex": 5},
        )
        assert updated["historySummary"] == "A summary of events"
        assert updated["historySummaryUpToIndex"] == 5

    def test_update_session_not_found(self, storage):
        result = storage.update_session(str(uuid.uuid4()), {"name": "Nope"})
        assert result is None


class TestDeleteSession:
    def test_delete_session(self, storage):
        session = storage.create_session(data_source="custom", name="Del")
        assert storage.delete_session(session["id"]) is True
        assert storage.get_session(session["id"]) is None

    def test_delete_session_not_found(self, storage):
        assert storage.delete_session(str(uuid.uuid4())) is False


class TestDeleteEmptySessions:
    def test_delete_empty_sessions(self, storage):
        # Session with messages (should survive)
        s1 = storage.create_session(data_source="custom", name="Active")
        storage.update_session(
            s1["id"], {"addMessage": {"role": "user", "content": "hi"}}
        )

        # Session without user messages (should be deleted)
        s2 = storage.create_session(data_source="custom", name="Empty")

        deleted_count = storage.delete_empty_sessions()
        assert deleted_count >= 1

        # Active session survives
        assert storage.get_session(s1["id"]) is not None
        # Empty session is gone
        assert storage.get_session(s2["id"]) is None


# ── Artifact tests ───────────────────────────────────────────


class TestCreateArtifact:
    def test_create_artifact(self, storage):
        session = storage.create_session(data_source="custom", name="Art")
        # Add an insight first
        session = storage.update_session(
            session["id"],
            {
                "addInsight": {
                    "title": "Finding",
                    "summary": "Details",
                    "visualization": {"type": "bar", "data": [{"x": 1, "y": 2}]},
                }
            },
        )
        insight_id = session["insights"][0]["id"]

        artifact = storage.create_artifact(
            session_id=session["id"],
            insight_id=insight_id,
            name="My Artifact",
            description="A saved insight",
        )
        assert artifact is not None
        assert artifact["name"] == "My Artifact"
        assert artifact["sessionId"] == session["id"]
        assert artifact["insightId"] == insight_id
        assert artifact["dataSource"] == "custom"
        assert "visualization" in artifact
        assert "dataSnapshot" in artifact
        uuid.UUID(artifact["id"])

        # Check that insight got savedAsArtifact link
        updated_session = storage.get_session(session["id"])
        linked_insight = updated_session["insights"][0]
        assert linked_insight["savedAsArtifact"] == artifact["id"]

    def test_create_artifact_session_not_found(self, storage):
        assert storage.create_artifact(str(uuid.uuid4()), "ins-1", "name", "desc") is None

    def test_create_artifact_insight_not_found(self, storage):
        session = storage.create_session(data_source="custom", name="NoIns")
        assert storage.create_artifact(session["id"], "bad-insight-id", "name", "desc") is None


class TestCreateReportArtifact:
    def test_create_report_artifact(self, storage):
        session = storage.create_session(data_source="custom", name="Report")
        viz = {"type": "report", "sections": [{"type": "text", "content": "Hello"}]}
        snap = {"data": [], "columns": [], "rowCount": 0, "capturedAt": "2025-01-01T00:00:00"}

        artifact = storage.create_report_artifact(
            session_id=session["id"],
            title="Q1 Report",
            description="Quarterly summary",
            visualization=viz,
            data_snapshot=snap,
        )
        assert artifact is not None
        assert artifact["name"] == "Q1 Report"
        assert artifact["visualization"] == viz
        assert artifact["dataSnapshot"] == snap
        assert artifact["insightId"] is None


class TestListArtifacts:
    def test_list_artifacts(self, storage):
        session = storage.create_session(data_source="custom", name="List")
        viz = {"type": "report", "sections": []}
        snap = {"data": [], "columns": [], "rowCount": 0, "capturedAt": "2025-01-01T00:00:00"}
        storage.create_report_artifact(session["id"], "A1", "", viz, snap)
        storage.create_report_artifact(session["id"], "A2", "", viz, snap)

        artifacts = storage.list_artifacts()
        assert len(artifacts) >= 2
        names = [a["name"] for a in artifacts]
        assert "A1" in names
        assert "A2" in names


class TestGetArtifact:
    def test_get_artifact(self, storage):
        session = storage.create_session(data_source="custom", name="Get")
        viz = {"type": "report", "sections": []}
        snap = {"data": [], "columns": [], "rowCount": 0, "capturedAt": "2025-01-01T00:00:00"}
        created = storage.create_report_artifact(session["id"], "Art", "", viz, snap)

        fetched = storage.get_artifact(created["id"])
        assert fetched is not None
        assert fetched["id"] == created["id"]
        assert fetched["name"] == "Art"

    def test_get_artifact_not_found(self, storage):
        assert storage.get_artifact(str(uuid.uuid4())) is None


class TestDeleteArtifact:
    def test_delete_artifact(self, storage):
        session = storage.create_session(data_source="custom", name="DelArt")
        session = storage.update_session(
            session["id"],
            {
                "addInsight": {
                    "title": "Finding",
                    "summary": "Details",
                    "visualization": {"type": "bar", "data": []},
                }
            },
        )
        insight_id = session["insights"][0]["id"]
        artifact = storage.create_artifact(session["id"], insight_id, "To Delete", "")

        assert storage.delete_artifact(artifact["id"]) is True
        assert storage.get_artifact(artifact["id"]) is None

        # savedAsArtifact should be cleared from insight
        updated = storage.get_session(session["id"])
        assert updated["insights"][0].get("savedAsArtifact") is None

    def test_delete_artifact_not_found(self, storage):
        assert storage.delete_artifact(str(uuid.uuid4())) is False
