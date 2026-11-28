"""Fact files: each table has status (confirmed or assumed) and source."""

import pytest

from rccar_mech import params


def write(tmp_path, text):
    p = tmp_path / "f.toml"
    p.write_text(text)
    return p


def test_fact_file_loads(tmp_path):
    p = write(tmp_path, '[a]\nx = 1.0\nstatus = "assumed"\nsource = "test"\n')
    assert params.load_facts(p)["a"]["x"] == 1.0


@pytest.mark.parametrize(
    "text",
    [
        "[a]\nx = 1.0\n",
        '[a]\nx = 1.0\nstatus = "assumed"\n',
        '[a]\nx = 1.0\nstatus = "guess"\nsource = "t"\n',
        '[a]\nx = 1.0\nstatus = "assumed"\nsource = ""\n',
    ],
)
def test_fact_table_without_status_or_source_is_rejected(tmp_path, text):
    with pytest.raises(params.ParamError):
        params.load_facts(write(tmp_path, text))


def test_design_file_needs_no_status(tmp_path):
    assert params.load_design(write(tmp_path, "x = 2.0\n"))["x"] == 2.0


def test_repo_print_file_is_valid():
    lim = params.load_facts(params.config_path("print.toml"))
    assert lim["limits"]["min_wall"] > 0
    assert lim["bed"]["x"] > 0


def test_assumed_lists_the_unconfirmed_tables(tmp_path):
    p = write(tmp_path, '[a]\nstatus = "assumed"\nsource = "t"\n[b]\nstatus = "confirmed"\nsource = "t"\n')
    assert params.assumed(params.load_facts(p)) == ["a"]
