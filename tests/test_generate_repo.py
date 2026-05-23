# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 nzbdav contributors

"""Tests for repository metadata generation."""

import importlib.util
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ADDON_DIR = REPO_ROOT / "repo" / "plugin.video.nzbdav"
REPO_ADDON_DIR = REPO_ROOT / "repo" / "repository.nzbdav"


def _load_generate_repo_module():
    script_path = REPO_ROOT / "scripts" / "generate_repo.py"
    spec = importlib.util.spec_from_file_location("generate_repo_script", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_generate_repo_writes_minimal_pages_root_files(tmp_path, monkeypatch):
    module = _load_generate_repo_module()
    monkeypatch.chdir(REPO_ROOT)

    output_dir = tmp_path / "pages"
    module.generate_repo(output_dir=str(output_dir))

    index_path = output_dir / "index.html"
    assert index_path.exists()
    contents = index_path.read_text(encoding="utf-8")
    assert "repository.nzbdav-" in contents
    assert ".zip" in contents
    assert "plugin.video.nzbdav-" not in contents
    assert (output_dir / ".nojekyll").exists()
    assert (output_dir / "addons.xml").exists()
    assert (output_dir / "addons.xml.md5").exists()
    assert not list(output_dir.glob("plugin.video.nzbdav-*.zip"))
    assert not (output_dir / "plugin.video.nzbdav").exists()


def test_generate_repo_html_indexes_use_standards_doctype(tmp_path, monkeypatch):
    module = _load_generate_repo_module()
    monkeypatch.chdir(REPO_ROOT)
    release_zip = tmp_path / "plugin.video.nzbdav-1.2.1.zip"
    release_addon_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<addon id="plugin.video.nzbdav" name="NZB-DAV" version="1.2.1" />
"""
    with zipfile.ZipFile(release_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("plugin.video.nzbdav/addon.xml", release_addon_xml)

    output_dir = tmp_path / "pages"
    module.generate_repo(output_dir=str(output_dir), addon_zip=str(release_zip))

    index_paths = [
        output_dir / "index.html",
        output_dir / "repository.nzbdav" / "index.html",
    ]
    for index_path in index_paths:
        contents = index_path.read_text(encoding="utf-8").lower()
        assert contents.startswith("<!doctype html>\n")
        assert "<head>" in contents
        assert "<body>" in contents


def test_generate_repo_omits_full_changelog_from_repo_index(tmp_path, monkeypatch):
    module = _load_generate_repo_module()
    monkeypatch.chdir(REPO_ROOT)

    output_dir = tmp_path / "pages"
    module.generate_repo(output_dir=str(output_dir))

    tree = ET.parse(output_dir / "addons.xml")
    addon = tree.find("./addon[@id='plugin.video.nzbdav']")
    assert addon is not None
    metadata = addon.find("./extension[@point='xbmc.addon.metadata']")
    assert metadata is not None
    assert metadata.find("news") is None


def test_generate_repo_includes_pages_repository_urls(tmp_path, monkeypatch):
    module = _load_generate_repo_module()
    monkeypatch.chdir(REPO_ROOT)

    output_dir = tmp_path / "pages"
    module.generate_repo(output_dir=str(output_dir))

    tree = ET.parse(output_dir / "addons.xml")
    repo = tree.find("./addon[@id='repository.nzbdav']")
    assert repo is not None
    repo_dir = repo.find("./extension[@point='xbmc.addon.repository']/dir")
    repo_base = "https://ponchopig.github.io/nzbdavkodi"
    assert repo_dir is not None
    assert repo_dir.findtext("info") == "{}/addons.xml".format(repo_base)
    assert repo_dir.findtext("checksum") == "{}/addons.xml.md5".format(repo_base)
    assert repo_dir.findtext("datadir") == "{}/".format(repo_base)


def test_generate_repo_fails_when_repository_addon_dir_is_missing(
    tmp_path, monkeypatch
):
    module = _load_generate_repo_module()
    monkeypatch.chdir(REPO_ROOT)

    missing_repo_dir = tmp_path / "missing-repository-addon"

    with pytest.raises(SystemExit) as excinfo:
        module.generate_repo(
            output_dir=str(tmp_path / "repo-output"),
            repository_addon_dir=str(missing_repo_dir),
        )

    assert str(excinfo.value) == (
        "generate_repo: repository addon directory not found: {!r}".format(
            str(missing_repo_dir)
        )
    )
    assert not (tmp_path / "repo-output" / "addons.xml").exists()


def test_generate_repo_writes_strict_md5_payload(tmp_path, monkeypatch):
    module = _load_generate_repo_module()
    monkeypatch.chdir(REPO_ROOT)

    output_dir = tmp_path / "pages"
    module.generate_repo(output_dir=str(output_dir))

    md5_payload = (output_dir / "addons.xml.md5").read_bytes()
    assert len(md5_payload) == 32
    assert md5_payload.decode("ascii").isalnum()


def test_generate_repo_can_publish_release_zip_instead_of_worktree_addon(
    tmp_path, monkeypatch
):
    module = _load_generate_repo_module()
    monkeypatch.chdir(REPO_ROOT)
    release_zip = tmp_path / "release-addon.zip"
    release_addon_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<addon id="plugin.video.nzbdav" name="NZB-DAV" version="1.0.3">
    <extension point="xbmc.addon.metadata">
        <summary lang="en">Release addon</summary>
        <news>release notes are too large for repository metadata</news>
        <assets>
            <icon>resources/icon.png</icon>
            <fanart>resources/fanart.jpg</fanart>
        </assets>
    </extension>
</addon>
"""
    with zipfile.ZipFile(release_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("plugin.video.nzbdav/addon.xml", release_addon_xml)
        zf.writestr("plugin.video.nzbdav/resources/icon.png", b"icon")
        zf.writestr("plugin.video.nzbdav/resources/fanart.jpg", b"fanart")

    output_dir = tmp_path / "pages"
    module.generate_repo(output_dir=str(output_dir), addon_zip=str(release_zip))

    tree = ET.parse(output_dir / "addons.xml")
    addon = tree.find("./addon[@id='plugin.video.nzbdav']")
    assert addon is not None
    assert addon.attrib["version"] == "1.0.3"
    metadata = addon.find("./extension[@point='xbmc.addon.metadata']")
    assert metadata is not None
    assert metadata.find("news") is None
    assert metadata.findtext("path") == (
        "https://github.com/PonchoPig/nzbdavkodi/releases/download/"
        "v1.0.3/plugin.video.nzbdav-1.0.3.zip"
    )
    assert not list(output_dir.glob("plugin.video.nzbdav-*.zip"))
    assert not (output_dir / "plugin.video.nzbdav").exists()


def test_generate_repo_writes_release_path_to_all_metadata_extensions(
    tmp_path, monkeypatch
):
    module = _load_generate_repo_module()
    monkeypatch.chdir(REPO_ROOT)
    release_zip = tmp_path / "plugin.video.nzbdav-1.0.4.zip"
    release_addon_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<addon id="plugin.video.nzbdav" name="NZB-DAV" version="1.0.4">
    <extension point="xbmc.addon.metadata">
        <summary lang="en">XBMC metadata</summary>
    </extension>
    <extension point="kodi.addon.metadata">
        <summary lang="en">Kodi metadata</summary>
    </extension>
</addon>
"""
    with zipfile.ZipFile(release_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("plugin.video.nzbdav/addon.xml", release_addon_xml)

    output_dir = tmp_path / "pages"
    module.generate_repo(output_dir=str(output_dir), addon_zip=str(release_zip))

    tree = ET.parse(output_dir / "addons.xml")
    addon = tree.find("./addon[@id='plugin.video.nzbdav']")
    assert addon is not None
    expected_path = (
        "https://github.com/PonchoPig/nzbdavkodi/releases/download/"
        "v1.0.4/plugin.video.nzbdav-1.0.4.zip"
    )

    for point in ("xbmc.addon.metadata", "kodi.addon.metadata"):
        metadata = addon.find("./extension[@point='{}']".format(point))
        assert metadata is not None
        assert metadata.findtext("path") == expected_path


def test_generate_repo_smoke_check_passes_for_generated_pages(tmp_path, monkeypatch):
    module = _load_generate_repo_module()
    monkeypatch.chdir(REPO_ROOT)
    release_zip = tmp_path / "plugin.video.nzbdav-1.2.1.zip"
    release_addon_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<addon id="plugin.video.nzbdav" name="NZB-DAV" version="1.2.1" />
"""
    with zipfile.ZipFile(release_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("plugin.video.nzbdav/addon.xml", release_addon_xml)

    output_dir = tmp_path / "pages"
    module.generate_repo(output_dir=str(output_dir), addon_zip=str(release_zip))

    module.smoke_check_pages(str(output_dir))


def test_generate_repo_smoke_check_rejects_copied_addon_zip(tmp_path, monkeypatch):
    module = _load_generate_repo_module()
    monkeypatch.chdir(REPO_ROOT)

    output_dir = tmp_path / "pages"
    module.generate_repo(output_dir=str(output_dir))
    (output_dir / "plugin.video.nzbdav-9.9.9.zip").write_bytes(b"bad")

    with pytest.raises(SystemExit) as excinfo:
        module.smoke_check_pages(str(output_dir))

    assert str(excinfo.value) == (
        "generate_repo: Pages artifact must not contain plugin.video.nzbdav zip files"
    )


def test_generate_repo_smoke_check_rejects_stale_repository_zip(tmp_path, monkeypatch):
    module = _load_generate_repo_module()
    monkeypatch.chdir(REPO_ROOT)

    output_dir = tmp_path / "pages"
    module.generate_repo(output_dir=str(output_dir))
    stale_zip = output_dir / "repository.nzbdav" / "repository.nzbdav-0.0.1.zip"
    stale_zip.write_bytes(b"bad")

    with pytest.raises(SystemExit) as excinfo:
        module.smoke_check_pages(str(output_dir))

    assert str(excinfo.value) == (
        "generate_repo: repository.nzbdav directory must contain one matching "
        "repository zip"
    )


def test_parse_local_xml_rejects_doctype(tmp_path):
    module = _load_generate_repo_module()
    addon_xml = tmp_path / "addon.xml"
    addon_xml.write_text(
        '<!DOCTYPE addon [<!ENTITY secret "x">]>\n<addon id="x" version="1.0.0" />',
        encoding="utf-8",
    )

    with pytest.raises(module.ET.ParseError):
        module._parse_local_xml(str(addon_xml))
