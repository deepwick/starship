import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

from deepwick_spec.ansi import runs
from deepwick_spec.check_port import check_port
from deepwick_spec.palette import ANSI_SLOTS, load_palette

REPO = Path(__file__).resolve().parents[1]
PALETTE = load_palette()
C = PALETTE.colors
STARSHIP_NAMES = {"magenta": "purple"}
requires_starship = pytest.mark.skipif(shutil.which("starship") is None, reason="requires starship")


def config():
    with open(REPO / "deepwick.toml", "rb") as f:
        return tomllib.load(f)


def test_selects_deepwick_palette():
    assert config()["palette"] == "deepwick"


def test_palette_overrides_all_16_color_names():
    palette = config()["palettes"]["deepwick"]
    for slot in ANSI_SLOTS:
        name = STARSHIP_NAMES.get(slot, slot)
        assert palette[name] == PALETTE.ansi[slot], name
        assert palette[f"bright-{name}"] == PALETTE.ansi["bright" + slot.capitalize()], name


def render(tmp_path, config_text):
    repo = tmp_path / "deepwick-sample"
    repo.mkdir(exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    cfg = tmp_path / "starship.toml"
    cfg.write_text(config_text)
    env = {**os.environ, "PWD": str(repo), "STARSHIP_CONFIG": str(cfg), "STARSHIP_SHELL": "", "STARSHIP_CACHE": str(tmp_path / "cache"), "GIT_CONFIG_GLOBAL": "/dev/null"}
    result = subprocess.run(["starship", "prompt"], cwd=repo, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result


def color_of(output, needle):
    for chunk, style in runs(output):
        if needle in chunk:
            return style["fg"]
    raise AssertionError(f"{needle!r} not in prompt")


@requires_starship
def test_default_modules_use_deepwick_colors(tmp_path):
    result = render(tmp_path, (REPO / "deepwick.toml").read_text())
    assert result.stderr == ""
    assert color_of(result.stdout, "deepwick-sample") == C["teal"].lower()
    assert color_of(result.stdout, "main") == C["magenta"].lower()


@requires_starship
def test_palette_line_must_be_top_level(tmp_path):
    existing = '[directory]\ntruncation_length = 2\n'
    appended = render(tmp_path, existing + "\n" + (REPO / "deepwick.toml").read_text())
    prepended = render(tmp_path, (REPO / "deepwick.toml").read_text() + "\n" + existing)
    assert color_of(prepended.stdout, "deepwick-sample") == C["teal"].lower()
    assert color_of(appended.stdout, "deepwick-sample") != C["teal"].lower()


def test_readme_warns_about_top_level_palette():
    assert "before any `[section]`" in (REPO / "README.md").read_text()


def test_port_conventions():
    assert check_port(REPO, PALETTE.allowed_hex()) == []
