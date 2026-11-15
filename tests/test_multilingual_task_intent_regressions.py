import pytest

from finzanjir_ai.orchestration.task_intent import classify_task_type


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        # Uzbek Cyrillic process marker: regression for a malformed word-boundary.
        ("FINZANJIRда шубҳали сигналдан кейинги босқичлар қандай?", "process"),
        ("Шубҳали сигналдан кейинги қадамлар қандай?", "process"),
        # Uzbek Cyrillic reason forms must not fall back to generic explanation.
        ("FINZANJIR нима учун яратилган?", "reason"),
        ("Лойиҳанинг асосий сабаби нима?", "reason"),
        # Other supported languages retain their task categories.
        ("Why was FINZANJIR created?", "reason"),
        ("Почему FINZANJIR не блокирует карту автоматически?", "reason"),
        ("FINZANJIR басқа елдерден несімен ерекшеленеді?", "comparison"),
        ("FINZANJIRning boshqa davlatlardagi tizimlardan farqi nimada?", "comparison"),
        ("What are the steps after a suspicious signal?", "process"),
        ("Қаржылық сигналдан кейін қандай кезеңдер болады?", "process"),
        ("Signalden keyin qanday basqıshlar bar?", "process"),
        ("Which components are already deployed and which are only planned?", "status_audit"),
        ("Какие части уже внедрены, а какие пока только планируются?", "status_audit"),
    ],
)
def test_multilingual_task_intent_regressions(query, expected):
    assert classify_task_type(query) == expected
