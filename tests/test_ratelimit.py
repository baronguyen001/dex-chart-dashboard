from __future__ import annotations

from dexscope.ratelimit import RateLimiter


def _fake_clock():
    state = {"t": 1000.0}
    sleeps: list[float] = []

    def clock() -> float:
        return state["t"]

    def sleep(secs: float) -> None:
        sleeps.append(secs)
        state["t"] += secs

    return clock, sleep, sleeps


def test_spaces_consecutive_calls():
    clock, sleep, sleeps = _fake_clock()
    rl = RateLimiter(2.0, clock=clock, sleep=sleep)
    rl.wait()  # first call: plenty of time has "elapsed" since 0 -> no sleep
    rl.wait()  # immediate second call -> must wait the full interval
    rl.wait()  # and again
    assert sleeps == [2.0, 2.0]


def test_zero_interval_never_sleeps():
    clock, sleep, sleeps = _fake_clock()
    rl = RateLimiter(0.0, clock=clock, sleep=sleep)
    rl.wait()
    rl.wait()
    assert sleeps == []


def test_negative_interval_clamped_to_zero():
    rl = RateLimiter(-5.0)
    assert rl.min_interval == 0.0
