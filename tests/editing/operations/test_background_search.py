import time

from autodrive_editor.editing.operations.background_search import BackgroundSearch


def wait_for(qapp, condition):
    deadline = time.monotonic() + 10

    while not condition() and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)


def test_the_result_comes_back_on_the_ui_thread(qapp):
    results, failures = [], []
    background = BackgroundSearch()
    background.start(lambda cancelled: 42, results.append, lambda: failures.append(1))

    wait_for(qapp, lambda: results)

    assert results == [42] and failures == []


def test_an_exception_is_logged_and_reported_as_failed(qapp, caplog):
    results, failures = [], []

    def search(cancelled):
        raise ValueError("broken")

    background = BackgroundSearch()
    background.start(search, results.append, lambda: failures.append(1))
    wait_for(qapp, lambda: failures)

    assert failures == [1] and results == []
    assert "Background search failed" in caplog.text and "broken" in caplog.text


def test_the_returned_event_cancels_the_search(qapp):
    results = []

    def search(cancelled):
        while not cancelled():
            time.sleep(0.01)

        return "stopped"

    background = BackgroundSearch()
    cancel = background.start(search, results.append, lambda: None)
    cancel.set()
    wait_for(qapp, lambda: results)

    assert results == ["stopped"]


def test_stop_cancels_running_searches_and_waits_for_them(qapp):
    ended = []

    def search(cancelled):
        while not cancelled():
            time.sleep(0.01)

        time.sleep(0.05)
        ended.append(1)

    background = BackgroundSearch()
    background.start(search, lambda result: None, lambda: None)
    background.stop()

    assert ended == [1]
