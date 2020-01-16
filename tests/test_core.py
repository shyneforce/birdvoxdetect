import datetime
import h5py
import numpy as np
import os
import pandas as pd
import pytest
import shutil
import soundfile as sf
import tempfile

from birdvoxdetect.birdvoxdetect_exceptions import BirdVoxDetectError
from birdvoxdetect.core import get_output_path, process_file


TEST_DIR = os.path.dirname(__file__)
TEST_AUDIO_DIR = os.path.join(TEST_DIR, 'data', 'audio')

NEGATIVE_MD5 = 'ff3d3feb-3371-44ad-a3b3-85969c2cd5ab'
POSITIVE_MD5 = 'fd79e55d-d3a3-4083-aba1-4f00b545c3d6'


def test_get_output_path():
    test_filepath = '/path/to/the/test/file/audio.wav'
    suffix = 'checklist.csv'
    test_output_dir = '/tmp/test/output/dir'
    exp_output_path = '/tmp/test/output/dir/audio_checklist.csv'
    output_path = get_output_path(test_filepath, suffix, test_output_dir)
    assert output_path == exp_output_path

    # No output directory
    exp_output_path = '/path/to/the/test/file/audio_checklist.csv'
    output_path = get_output_path(test_filepath, suffix)
    assert output_path == exp_output_path

    # No suffix
    exp_output_path = '/path/to/the/test/file/audio.csv'
    output_path = get_output_path(test_filepath, '.csv')
    assert output_path == exp_output_path


def test_process_file():
    # non-existing path
    invalid_filepath = 'path/to/a/nonexisting/file.wav'
    pytest.raises(BirdVoxDetectError, process_file, invalid_filepath)

    # non-audio path
    nonaudio_existing_filepath = '/Users/vl238'
    pytest.raises(BirdVoxDetectError, process_file, nonaudio_existing_filepath)

    # non-existing model
    pytest.raises(
        BirdVoxDetectError,
        process_file,
        os.path.join(TEST_AUDIO_DIR, POSITIVE_MD5 + '.wav'),
        detector_name="a_birdvoxdetect_model_that_does_not_exist")

    # non-existing model
    pytest.raises(
        BirdVoxDetectError,
        process_file,
        os.path.join(TEST_AUDIO_DIR, POSITIVE_MD5 + '.wav'),
        detector_name="birdvoxdetect_empty")

    # standard call
    # this example has one flight call (SWTH) at 8.79 seconds
    tempdir = tempfile.mkdtemp()
    process_file(
        os.path.join(TEST_AUDIO_DIR, POSITIVE_MD5 + '.wav'),
        output_dir=os.path.join(tempdir, "subfolder"))
    csv_path = os.path.join(
        tempdir, "subfolder",
        POSITIVE_MD5 + '_checklist.csv')
    assert os.path.exists(csv_path)
    df = pd.read_csv(csv_path)
    assert len(df) == 1
    assert len(df.columns) == 3
    assert df.columns[0] == "Time (hh:mm:ss)"
    assert df.columns[1] == "Species (4-letter code)"
    assert df.columns[2] == "Confidence (%)"
    df_strptime = datetime.datetime.strptime(
        list(df["Time (hh:mm:ss)"])[0], '%H:%M:%S.%f')
    df_timedelta = df_strptime - datetime.datetime.strptime(
        '00:00:00.00', '%H:%M:%S.%f')
    assert np.allclose(
        np.array([df_timedelta.total_seconds()]), np.array([8.79]), atol=0.1)
    assert list(df["Species (4-letter code)"])[0] == "SWTH"
    shutil.rmtree(tempdir

    # standard call on clip without any flight call
    tempdir = tempfile.mkdtemp()
    process_file(
        os.path.join(TEST_AUDIO_DIR, NEGATIVE_MD5 + '.wav'),
        output_dir=os.path.join(tempdir, "subfolder"))
    csv_path = os.path.join(
        tempdir, "subfolder",
        NEGATIVE_MD5 + '_checklist.csv')
    df = pd.read_csv(csv_path)
    assert len(df) == 0

    # export clips
    tempdir = tempfile.mkdtemp()
    process_file(
        os.path.join(TEST_AUDIO_DIR, POSITIVE_MD5 + '.wav'),
        output_dir=tempdir,
        export_clips=True)
    clips_dir = os.path.join(
        tempdir, POSITIVE_MD5 + '_clips')
    assert os.path.exists(clips_dir)
    clips_list = sorted(os.listdir(clips_dir))
    assert len(clips_list) == 1
    assert clips_list[0].startswith(POSITIVE_MD5 + '_00_00_08-78')
    assert clips_list[0].endswith('SWTH.wav')
    assert np.all([c.endswith(".wav") for c in clips_list])
    shutil.rmtree(tempdir)

    # export confidence
    tempdir = tempfile.mkdtemp()
    process_file(
        os.path.join(TEST_AUDIO_DIR, POSITIVE_MD5 + '.wav'),
        output_dir=tempdir,
        export_confidence=True)
    confidence_path = os.path.join(
        tempdir, POSITIVE_MD5 + '_confidence.hdf5')
    with h5py.File(confidence_path, "r") as f:
        confidence = f["confidence"][()]
    assert confidence.shape == (199,)
    shutil.rmtree(tempdir)

    # suffix
    tempdir = tempfile.mkdtemp()
    process_file(
        os.path.join(TEST_AUDIO_DIR, POSITIVE_MD5 + '.wav'),
        output_dir=tempdir,
        suffix="mysuffix")
    csv_path = os.path.join(
        tempdir,
        POSITIVE_MD5 + '_mysuffix_checklist.csv')
    assert os.path.exists(csv_path)
    shutil.rmtree(tempdir)
