"""test_jobs exercises the streaming utilities in jobs."""

import contextlib
import io
import json
from pathlib import Path

import pytest
from withpi import AsyncPiClient, PiClient
from withpi.types.data import (
    GenerateInputResponsePairStartJobParams,
    GenerateStartJobParams,
)
from withpi.types.scoring_system import CalibrateStartJobParams

from withpi_utils import stream, stream_async

DATADIR = Path(__file__).resolve().parent / "data"

pytestmark = pytest.mark.integration


@pytest.fixture()
def pi_client() -> PiClient:
    return PiClient()


@pytest.fixture()
def async_pi_client() -> AsyncPiClient:
    return AsyncPiClient()


@pytest.fixture()
def calibrate_request() -> CalibrateStartJobParams:
    path = DATADIR / "calibrate_request.json"
    return json.loads(path.read_bytes())


@pytest.fixture()
def synthetic_data_request() -> GenerateInputResponsePairStartJobParams:
    path = DATADIR / "synthetic_data_request.json"
    return json.loads(path.read_bytes())


@pytest.fixture()
def seed_request() -> GenerateStartJobParams:
    path = DATADIR / "seed_request.json"
    return json.loads(path.read_bytes())


def test_calibrate_sync(pi_client, calibrate_request):
    response = pi_client.scoring_system.calibrate.start_job(**calibrate_request)
    assert response.state == "QUEUED"
    print(f"Calibration started on job {response.job_id}")

    with io.StringIO() as buf, contextlib.redirect_stdout(buf):
        for data in stream(pi_client.scoring_system.calibrate, response):
            # Should not have yielded any data
            assert False
        printed = buf.getvalue()
    print(printed)
    assert "DONE" in printed
    final_response = pi_client.scoring_system.calibrate.retrieve(response.job_id)
    assert final_response.state == "DONE"


@pytest.mark.asyncio
async def test_calibrate_async(async_pi_client, calibrate_request):
    response = await async_pi_client.scoring_system.calibrate.start_job(
        **calibrate_request
    )
    assert response.state == "QUEUED"
    print(f"Started job {response.job_id}")

    with io.StringIO() as buf, contextlib.redirect_stdout(buf):
        async for data in stream_async(
            async_pi_client.scoring_system.calibrate, response
        ):
            # Should not have yielded any data
            assert False
        printed = buf.getvalue()
    print(printed)
    assert "DONE" in printed
    final_response = await async_pi_client.scoring_system.calibrate.retrieve(
        response.job_id
    )
    assert final_response.state == "DONE"


def test_synthetic_data_sync(pi_client, synthetic_data_request):
    response = pi_client.data.generate_input_response_pairs.start_job(
        **synthetic_data_request
    )
    assert response.state == "QUEUED"
    print(f"Started job {response.job_id}")

    generated_data = []
    with io.StringIO() as buf, contextlib.redirect_stdout(buf):
        for data in stream(pi_client.data.generate_input_response_pairs, response):
            generated_data.append(data)
        printed = buf.getvalue()
    for data in generated_data:
        print(f"Generated data: {data}")
    print(printed)
    assert len(generated_data) > 2
    assert "DONE" in printed
    final_response = pi_client.data.generate_input_response_pairs.retrieve(
        response.job_id
    )
    assert final_response.state == "DONE"


@pytest.mark.asyncio
async def test_synthetic_data_async(async_pi_client, synthetic_data_request):
    response = await async_pi_client.data.generate_input_response_pairs.start_job(
        **synthetic_data_request
    )
    assert response.state == "QUEUED"
    print(f"Started job {response.job_id}")

    generated_data = []
    with io.StringIO() as buf, contextlib.redirect_stdout(buf):
        async for data in stream_async(
            async_pi_client.data.generate_input_response_pairs, response
        ):
            generated_data.append(data)
        printed = buf.getvalue()
    for data in generated_data:
        print(f"Generated data: {data}")
    print(printed)
    assert len(generated_data) > 2
    assert "DONE" in printed
    final_response = await async_pi_client.data.generate_input_response_pairs.retrieve(
        response.job_id
    )
    assert final_response.state == "DONE"


def test_seeds_sync(pi_client, seed_request):
    response = pi_client.data.generate.start_job(**seed_request)
    assert response.state == "QUEUED"
    print(f"Started job {response.job_id}")

    generated_data = []
    with io.StringIO() as buf, contextlib.redirect_stdout(buf):
        for data in stream(pi_client.data.generate, response):
            generated_data.append(data)
        printed = buf.getvalue()
    for data in generated_data:
        print(f"Generated data: {data}")
    print(printed)
    assert len(generated_data) > 2
    assert "DONE" in printed
    final_response = pi_client.data.generate.retrieve(response.job_id)
    assert final_response.state == "DONE"


@pytest.mark.asyncio
async def test_seeds_async(async_pi_client, seed_request):
    response = await async_pi_client.data.generate.start_job(**seed_request)
    assert response.state == "QUEUED"
    print(f"Started job {response.job_id}")

    generated_data = []
    with io.StringIO() as buf, contextlib.redirect_stdout(buf):
        async for data in stream_async(async_pi_client.data.generate, response):
            generated_data.append(data)
        printed = buf.getvalue()
    for data in generated_data:
        print(f"Generated data: {data}")
    print(printed)
    assert len(generated_data) > 2
    assert "DONE" in printed
    final_response = await async_pi_client.data.generate.retrieve(response.job_id)
    assert final_response.state == "DONE"
