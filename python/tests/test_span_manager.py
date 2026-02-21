from wire.store.span_manager import SpanManager


class TestSpanManager:
    def test_initial_state(self):
        sm = SpanManager()
        assert sm.current_span is None
        assert sm.spans == {}

    def test_start_span(self):
        sm = SpanManager()
        auto_closed = sm.start("span1")
        assert auto_closed is None
        assert sm.current_span == "span1"
        assert "span1" in sm.spans
        assert sm.spans["span1"]["stopped_at"] is None

    def test_stop_span(self):
        sm = SpanManager()
        sm.start("span1")
        stopped = sm.stop()
        assert stopped == "span1"
        assert sm.current_span is None
        assert sm.spans["span1"]["stopped_at"] is not None

    def test_stop_when_no_span(self):
        sm = SpanManager()
        assert sm.stop() is None

    def test_auto_close(self):
        sm = SpanManager()
        sm.start("span1")
        auto_closed = sm.start("span2")
        assert auto_closed == "span1"
        assert sm.current_span == "span2"
        assert sm.spans["span1"]["stopped_at"] is not None
        assert sm.spans["span2"]["stopped_at"] is None

    def test_has_span(self):
        sm = SpanManager()
        assert not sm.has_span("span1")
        sm.start("span1")
        assert sm.has_span("span1")

    def test_reset(self):
        sm = SpanManager()
        sm.start("span1")
        sm.reset()
        assert sm.current_span is None
        assert sm.spans == {}
