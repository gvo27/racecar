"""Host-side unit tests (no hardware). Run: make unit"""
import rccar


def test_parse_kv_numbers_and_strings():
    assert rccar.parse_kv("TEL t=1 hdg=2.5 mode=RAW") == {"t": 1.0, "hdg": 2.5, "mode": "RAW"}


def test_parse_kv_ignores_prefix_and_bare_tokens():
    assert rccar.parse_kv("EVT FAILSAFE armed=0") == {"armed": 0.0}


def test_tuning_file_has_every_firmware_key():
    tuning = rccar.load_tuning()
    for (table, key), _cmd in rccar.FIRMWARE_KEYS:
        rccar.tuning_value(tuning, table, key)  # KeyError = tuning.toml / FIRMWARE_KEYS drift


def test_update_tuning_file_keeps_comments(tmp_path):
    f = tmp_path / "t.toml"
    f.write_text("[steering]\nservo_hz = 50   # frame rate\n")
    rccar.update_tuning_file({"servo_hz": 100}, f)
    assert f.read_text() == "[steering]\nservo_hz = 100   # frame rate\n"
