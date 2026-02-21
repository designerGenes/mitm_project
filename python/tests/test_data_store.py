from tests.conftest import make_exchange

from watcher.store.data_store import DataStore


class TestDataStore:
    def test_add_and_count(self):
        store = DataStore()
        assert store.count() == 0
        store.add(make_exchange())
        assert store.count() == 1

    def test_reset(self):
        store = DataStore()
        store.add(make_exchange())
        store.add(make_exchange())
        assert store.count() == 2
        store.reset()
        assert store.count() == 0

    def test_exchanges_property(self):
        store = DataStore()
        ex = make_exchange()
        store.add(ex)
        assert store.exchanges[0] is ex


class TestDataStoreFilter:
    def test_filter_by_span(self):
        store = DataStore()
        store.add(make_exchange(span="span1"))
        store.add(make_exchange(span="span2"))
        store.add(make_exchange(span=None))

        assert len(store.filter(span="span1")) == 1
        assert len(store.filter(span=None)) == 1
        # No filter (default ellipsis) returns all
        assert len(store.filter()) == 3

    def test_filter_by_domain(self):
        store = DataStore()
        store.add(make_exchange(domain="api.example.com"))
        store.add(make_exchange(domain="cdn.example.com"))

        assert len(store.filter(domain="api.example.com")) == 1
        assert len(store.filter(domain="cdn.example.com")) == 1

    def test_filter_by_endpoint(self):
        store = DataStore()
        store.add(make_exchange(endpoint="/users"))
        store.add(make_exchange(endpoint="/posts"))

        assert len(store.filter(endpoint="/users")) == 1

    def test_filter_by_method(self):
        store = DataStore()
        store.add(make_exchange(method="GET"))
        store.add(make_exchange(method="POST"))

        assert len(store.filter(method="GET")) == 1
        assert len(store.filter(method="post")) == 1  # case-insensitive

    def test_filter_endpoint_trailing_slash(self):
        store = DataStore()
        store.add(make_exchange(endpoint="/users"))

        assert len(store.filter(endpoint="/users/")) == 1

    def test_filter_combined(self):
        store = DataStore()
        store.add(make_exchange(span="s1", domain="api.example.com", method="GET"))
        store.add(make_exchange(span="s1", domain="api.example.com", method="POST"))
        store.add(make_exchange(span="s2", domain="api.example.com", method="GET"))

        result = store.filter(span="s1", domain="api.example.com", method="GET")
        assert len(result) == 1

    def test_filter_sorted_by_timestamp(self):
        from datetime import datetime, timezone, timedelta

        store = DataStore()
        t1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        t2 = t1 + timedelta(seconds=10)
        store.add(make_exchange(timestamp_start=t2))
        store.add(make_exchange(timestamp_start=t1))

        result = store.filter()
        assert result[0].timestamp_start == t1
        assert result[1].timestamp_start == t2
