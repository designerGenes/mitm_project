from wire.query.key_path import parse_key_path, resolve_key_path


class TestParseKeyPath:
    def test_simple_key(self):
        assert parse_key_path("name") == ["name"]

    def test_dotted(self):
        assert parse_key_path("user.name") == ["user", "name"]

    def test_bracket_index(self):
        assert parse_key_path("users[0]") == ["users", 0]

    def test_bracket_then_dot(self):
        assert parse_key_path("users[0].name") == ["users", 0, "name"]

    def test_root_bracket(self):
        assert parse_key_path("[0].name") == [0, "name"]

    def test_root_bracket_only(self):
        assert parse_key_path("[2]") == [2]

    def test_nested_arrays(self):
        assert parse_key_path("data.teams[0].members[1].role") == [
            "data", "teams", 0, "members", 1, "role"
        ]

    def test_empty(self):
        assert parse_key_path("") == []


class TestResolveKeyPath:
    def test_simple_dict(self):
        data = {"name": "Alice"}
        found, value, reason = resolve_key_path(data, "name")
        assert found is True
        assert value == "Alice"

    def test_nested_dict(self):
        data = {"user": {"name": "Bob"}}
        found, value, _ = resolve_key_path(data, "user.name")
        assert found is True
        assert value == "Bob"

    def test_array_index(self):
        data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
        found, value, _ = resolve_key_path(data, "users[1].name")
        assert found is True
        assert value == "Bob"

    def test_root_array(self):
        data = [{"id": 1}, {"id": 2}]
        found, value, _ = resolve_key_path(data, "[0].id")
        assert found is True
        assert value == 1

    def test_root_array_only(self):
        data = ["a", "b", "c"]
        found, value, _ = resolve_key_path(data, "[2]")
        assert found is True
        assert value == "c"

    def test_nested_arrays(self):
        data = {"data": {"teams": [{"members": [{"role": "admin"}, {"role": "user"}]}]}}
        found, value, _ = resolve_key_path(data, "data.teams[0].members[1].role")
        assert found is True
        assert value == "user"

    def test_key_not_found(self):
        data = {"name": "Alice"}
        found, value, reason = resolve_key_path(data, "age")
        assert found is False
        assert reason == "key_not_found"

    def test_index_out_of_bounds(self):
        data = [1, 2, 3]
        found, value, reason = resolve_key_path(data, "[5]")
        assert found is False
        assert reason == "index_out_of_bounds"

    def test_key_on_non_dict(self):
        data = {"name": "Alice"}
        found, value, reason = resolve_key_path(data, "name.first")
        assert found is False
        assert reason == "key_not_found"

    def test_index_on_non_list(self):
        data = {"name": "Alice"}
        found, value, reason = resolve_key_path(data, "name[0]")
        assert found is False
        assert reason == "key_not_found"

    def test_empty_path(self):
        data = {"key": "value"}
        found, value, _ = resolve_key_path(data, "")
        assert found is True
        assert value == data

    def test_deeply_nested(self):
        data = {"a": {"b": {"c": {"d": 42}}}}
        found, value, _ = resolve_key_path(data, "a.b.c.d")
        assert found is True
        assert value == 42

    def test_null_value(self):
        data = {"key": None}
        found, value, _ = resolve_key_path(data, "key")
        assert found is True
        assert value is None
