"""Tests for ``cubi_sak.sea_snap.pull_isa``.

We only run some smoke tests here.
"""

import os

import pytest
import filecmp
import glob
import linecache
import tokenize
from pyfakefs import fake_filesystem, fake_pathlib
from pyfakefs.fake_filesystem_unittest import Patcher

from cubi_sak.sea_snap.pull_isa import URL_TPL
from cubi_sak.__main__ import setup_argparse, main


def test_run_seasnap_pull_isa_help(capsys):
    parser, subparsers = setup_argparse()
    with pytest.raises(SystemExit) as e:
        parser.parse_args(["sea-snap", "pull-isa", "--help"])

    assert e.value.code == 0

    res = capsys.readouterr()
    assert res.out
    assert not res.err


def test_run_seasnap_pull_isa_nothing(capsys):
    parser, subparsers = setup_argparse()

    with pytest.raises(SystemExit) as e:
        parser.parse_args(["sea-snap", "pull-isa"])

    assert e.value.code == 2

    res = capsys.readouterr()
    assert not res.out
    assert res.err


@pytest.fixture
def fs_reload_sut():
    patcher = Patcher(modules_to_reload=[setup_argparse, main])
    patcher.setUp()
    linecache.open = patcher.original_open
    tokenize._builtin_open = patcher.original_open
    yield patcher.fs
    patcher.tearDown()


def test_run_seasnap_pull_isa_smoke_test(tmp_path, requests_mock, capsys, mocker, fs_reload_sut):
    project_uuid = "466ab946-ce6a-4c78-9981-19b79e7bbe86"
    argv = ["sea-snap", "pull-isa", "--sodar-auth-token", "XXX", project_uuid]

    parser, subparsers = setup_argparse()
    args = parser.parse_args(argv)

    fs = fs_reload_sut

    path_json = os.path.join(os.path.dirname(__file__), "data", "isa_test.json")
    fs.add_real_file(path_json)
    with open(path_json, "rt") as inputf:
        json_text = inputf.read()

    url = URL_TPL % {"sodar_url": args.sodar_url, "project_uuid": project_uuid, "api_key": "XXX"}
    requests_mock.get(url, text=json_text)

    fake_open = fake_filesystem.FakeFileOpen(fs)
    fake_os = fake_filesystem.FakeOsModule(fs)
    fake_pathl = fake_pathlib.FakePathlibModule(fs)

    mocker.patch("cubi_sak.sea_snap.pull_isa.open", fake_open)
    mocker.patch("pathlib.Path", fake_pathl.Path)
    mocker.patch("filecmp.open", fake_open)
    mocker.patch("filecmp.os", fake_os)

    res = main(argv)  # run as end-to-end test
    assert not res

    test_dir = os.path.join(os.path.dirname(__file__), "data", "ISA_files_test")
    fs.add_real_directory(test_dir)
    files = glob.glob(os.path.join(test_dir, "*"))

    match, mismatch, errors = filecmp.cmpfiles(
        "ISA_files", test_dir, (os.path.basename(f) for f in files), shallow=False
    )
    print([match, mismatch, errors])
    assert len(mismatch) == 0
    assert len(errors) == 0

    res = capsys.readouterr()
    assert not res.err
