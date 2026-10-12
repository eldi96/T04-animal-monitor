from app.api.routes import router


def test_public_replay_routes_are_registered_separately_from_live_collection():
    replay_paths = {
        (route.path, frozenset(route.methods or []))
        for route in router.routes
        if route.path.startswith("/api/replay/")
    }
    assert ("/api/replay/package", frozenset({"GET"})) in replay_paths
    assert ("/api/replay/state", frozenset({"GET"})) in replay_paths
    assert ("/api/replay/reset", frozenset({"POST"})) in replay_paths
    assert ("/api/replay/fixtures/{fixture_id}", frozenset({"POST"})) in replay_paths
    assert ("/api/replay/recover", frozenset({"POST"})) in replay_paths


def test_synthetic_replay_endpoints_do_not_share_live_collect_paths():
    route_paths = {route.path for route in router.routes}
    assert "/api/collect/today" in route_paths
    assert "/api/test/failure/{failure_type}" not in route_paths
    assert "/api/replay/fixtures/{fixture_id}" in route_paths
