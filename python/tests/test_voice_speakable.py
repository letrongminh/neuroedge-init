"""
A model's Markdown is shown, never read aloud: `speakable()` shapes what the voice says,
`VoiceSession._speak` sends TTS only that, and System 2 is asked to answer plainly.
"""

from __future__ import annotations

import asyncio

import pytest

from neuroedge.perception import VirtualClock, VoiceSession
from neuroedge.perception.providers import FakeSpeechToText, FakeTextToSpeech
from neuroedge.perception.providers.base import speakable
from neuroedge.sim import SimSession
from neuroedge.sim import session as sim_session

from .test_voice_speech import PARAMS, door  # noqa: F401 - the fixture

NEWS = (
    "Hiện tại có một số tin tức đáng chú ý như sau:\n\n"
    "*   **Thời tiết:** Hà Nội bắt đầu se lạnh.\n"
    "*   **Điện năng:** Giá điện sinh hoạt sẽ tăng"
)


@pytest.mark.parametrize(
    ("text", "spoken"),
    [
        ("Đã bật đèn hiên cho bạn rồi nhé!", "Đã bật đèn hiên cho bạn rồi nhé!"),
        (
            NEWS,
            "Hiện tại có một số tin tức đáng chú ý như sau: Thời tiết: Hà Nội bắt đầu se lạnh. "
            "Điện năng: Giá điện sinh hoạt sẽ tăng",
        ),
        ("## Tin mới\n1. Một\n2) Hai", "Tin mới. Một. Hai"),
        ("Xem [chi tiết](https://example.com) tại `vnexpress`", "Xem chi tiết tại vnexpress"),
        ("***rất*** quan trọng, __nhớ__ nhé", "rất quan trọng, nhớ nhé"),
        ("> trích dẫn", "trích dẫn"),
        ("phòng_101 mở", "phòng_101 mở"),  # a lone underscore is not emphasis
        ("***\n\n", ""),
    ],
)
def test_speakable_drops_markdown_and_keeps_the_words(text, spoken):
    assert speakable(text) == spoken


def test_tts_hears_the_words_not_the_markdown(door):  # noqa: F811 - the fixture
    clock = VirtualClock()
    session = SimSession.load(door, clock=clock)
    tts = FakeTextToSpeech(ms_per_char=10)
    voice = VoiceSession(session, clock=clock, params=PARAMS, stt=FakeSpeechToText([]), tts=tts)
    asyncio.run(voice._speak(["**Đèn** đã bật.", "***", NEWS]))
    assert tts.texts == [speakable("**Đèn** đã bật."), speakable(NEWS)]
    assert all("*" not in said for said in tts.texts)
    session.close()


def test_system_two_is_asked_to_answer_as_speech():
    assert sim_session.SPOKEN_STYLE in sim_session.CONVERSE_INSTRUCTIONS
    assert "không markdown" in sim_session.SPOKEN_STYLE
    source = sim_session.__loader__.get_source(sim_session.__name__)
    assert source.count("SPOKEN_STYLE") >= 3  # defined, converse, knowledge
