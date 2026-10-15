import importlib

import pytest
from fastapi import HTTPException


def test_deployed_frontend_and_api_share_one_origin(monkeypatch, tmp_path):
    import app.main as main

    (tmp_path / "index.html").write_text("<html>T04</html>", encoding="utf-8")
    (tmp_path / "app.js").write_text("console.log('T04')", encoding="utf-8")
    monkeypatch.setenv("T04_STATIC_DIR", str(tmp_path))
    try:
        deployed = importlib.reload(main)
        assert deployed.health() == {"status": "ok"}
        assert deployed.frontend("").path == tmp_path / "index.html"
        assert deployed.frontend("analysis").path == tmp_path / "index.html"
        assert deployed.frontend("app.js").path == tmp_path / "app.js"
        for path in ["missing.js", "api/missing", "../README.md"]:
            with pytest.raises(HTTPException) as error:
                deployed.frontend(path)
            assert error.value.status_code == 404
        assert any(getattr(route, "path", None) == "/{path:path}" for route in deployed.app.routes)
    finally:
        monkeypatch.delenv("T04_STATIC_DIR")
        importlib.reload(main)
