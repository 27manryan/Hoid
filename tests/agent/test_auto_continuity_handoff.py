from types import SimpleNamespace

from agent.conversation_compression import _write_auto_continuity_handoff


class _FakeSessionDb:
    def get_session_title(self, session_id):
        return "Long running task"


def test_auto_continuity_handoff_writes_vault_file(tmp_path, monkeypatch):
    vault = tmp_path / "Athenaeum"
    handoffs = vault / "system" / "handoffs"
    handoffs.mkdir(parents=True)
    (vault / "AGENTS.md").write_text("rules", encoding="utf-8")

    monkeypatch.chdir(vault)

    compressor = SimpleNamespace(
        context_length=1000,
        _previous_summary="## Active Task\nKeep going.\n\n## Critical Context\nImportant detail.",
    )
    agent = SimpleNamespace(
        cwd=str(vault),
        session_id="20260625_123456abcdef",
        context_compressor=compressor,
        _session_db=_FakeSessionDb(),
    )

    _write_auto_continuity_handoff(
        agent,
        messages=[{"role": "user", "content": "hello"}],
        compressed_messages=[],
        approx_tokens=870,
    )

    files = list(handoffs.glob("*_summary_hoid-autocontinuity-*.md"))
    assert len(files) == 1
    text = files[0].read_text(encoding="utf-8")
    assert "type: summary" in text
    assert "reconcile: hoid-dialectic" in text
    assert "Approximate context load at trigger: 87.0%." in text
    assert "## Compression summary" in text
    assert "Important detail." in text


def test_auto_continuity_handoff_redacts_secret_like_values(tmp_path, monkeypatch):
    vault = tmp_path / "Athenaeum"
    handoffs = vault / "system" / "handoffs"
    handoffs.mkdir(parents=True)
    (vault / "AGENTS.md").write_text("rules", encoding="utf-8")
    monkeypatch.chdir(vault)

    agent = SimpleNamespace(
        cwd=str(vault),
        session_id="s1",
        context_compressor=SimpleNamespace(context_length=1000, _previous_summary=""),
        _session_db=None,
    )
    compressed = [
        {
            "role": "user",
            "content": (
                '## Active Task\nUse {"api_key": "supersecretvalue"}.\n\n'
                "## Critical Context\nkeep path"
            ),
        }
    ]

    _write_auto_continuity_handoff(agent, [], compressed, approx_tokens=870)

    text = next(handoffs.glob("*_summary_hoid-autocontinuity-*.md")).read_text(
        encoding="utf-8"
    )
    assert "supersecretvalue" not in text
    assert '"api_key": "***"' in text
