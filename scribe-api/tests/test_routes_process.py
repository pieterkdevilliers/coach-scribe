"""Tests for POST /transcribe, /extract, and /process endpoints."""


async def test_transcribe_returns_job_id(api_client, mock_pool):
    resp = await api_client.post(
        "/transcribe",
        files={"file": ("audio.wav", b"fake audio data", "audio/wav")},
        data={"language": "en"},
    )
    assert resp.status_code == 200
    assert resp.json()["job_id"] == "test-job-id-123"


async def test_transcribe_enqueues_correct_job(api_client, mock_pool):
    await api_client.post(
        "/transcribe",
        files={"file": ("audio.mp4", b"fake video data", "video/mp4")},
        data={"language": "fr", "timestamps": "true"},
    )
    mock_pool.enqueue_job.assert_called_once()
    call_args = mock_pool.enqueue_job.call_args[0]
    assert call_args[0] == "transcribe_job"
    assert call_args[2] == "fr"   # language
    assert call_args[3] is True   # timestamps


async def test_transcribe_missing_file_returns_422(api_client):
    resp = await api_client.post("/transcribe", data={"language": "en"})
    assert resp.status_code == 422


async def test_extract_returns_job_id(api_client, mock_pool):
    resp = await api_client.post(
        "/extract",
        json={"transcript": "hello world", "prompt": "summarise"},
    )
    assert resp.status_code == 200
    assert resp.json()["job_id"] == "test-job-id-123"


async def test_extract_enqueues_correct_job(api_client, mock_pool):
    await api_client.post(
        "/extract",
        json={"transcript": "the transcript", "prompt": "the prompt"},
    )
    mock_pool.enqueue_job.assert_called_once_with(
        "extract_job", "the transcript", "the prompt"
    )


async def test_extract_missing_transcript_returns_422(api_client):
    resp = await api_client.post("/extract", json={"prompt": "summarise"})
    assert resp.status_code == 422


async def test_extract_missing_prompt_returns_422(api_client):
    resp = await api_client.post("/extract", json={"transcript": "some text"})
    assert resp.status_code == 422


async def test_process_returns_job_id(api_client, mock_pool):
    resp = await api_client.post(
        "/process",
        files={"file": ("audio.wav", b"fake audio data", "audio/wav")},
        data={"prompt": "summarise this call"},
    )
    assert resp.status_code == 200
    assert resp.json()["job_id"] == "test-job-id-123"


async def test_process_enqueues_correct_job(api_client, mock_pool):
    await api_client.post(
        "/process",
        files={"file": ("audio.wav", b"fake audio data", "audio/wav")},
        data={"prompt": "my prompt", "language": "de"},
    )
    mock_pool.enqueue_job.assert_called_once()
    call_args = mock_pool.enqueue_job.call_args[0]
    assert call_args[0] == "process_job"
    assert call_args[2] == "my prompt"  # prompt
    assert call_args[3] == "de"         # language


async def test_process_missing_prompt_returns_422(api_client):
    resp = await api_client.post(
        "/process",
        files={"file": ("audio.wav", b"fake audio data", "audio/wav")},
    )
    assert resp.status_code == 422


async def test_transcribe_url_returns_job_id(api_client, mock_pool):
    resp = await api_client.post(
        "/transcribe-url",
        json={"s3_url": "https://bucket.s3.amazonaws.com/call.mp4"},
    )
    assert resp.status_code == 200
    assert resp.json()["job_id"] == "test-job-id-123"


async def test_transcribe_url_enqueues_correct_job(api_client, mock_pool):
    await api_client.post(
        "/transcribe-url",
        json={"s3_url": "https://bucket.s3.amazonaws.com/call.mp4", "language": "fr"},
    )
    mock_pool.enqueue_job.assert_called_once()
    call_args = mock_pool.enqueue_job.call_args[0]
    assert call_args[0] == "transcribe_url_job"
    assert call_args[1] == "https://bucket.s3.amazonaws.com/call.mp4"
    assert call_args[2] == "fr"


async def test_transcribe_url_missing_url_returns_422(api_client):
    resp = await api_client.post("/transcribe-url", json={"language": "en"})
    assert resp.status_code == 422


async def test_process_url_returns_job_id(api_client, mock_pool):
    resp = await api_client.post(
        "/process-url",
        json={
            "s3_url": "https://bucket.s3.amazonaws.com/call.mp4",
            "prompt": "summarise",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["job_id"] == "test-job-id-123"


async def test_process_url_enqueues_correct_job(api_client, mock_pool):
    await api_client.post(
        "/process-url",
        json={
            "s3_url": "https://bucket.s3.amazonaws.com/call.mp4",
            "prompt": "my prompt",
            "language": "de",
        },
    )
    mock_pool.enqueue_job.assert_called_once()
    call_args = mock_pool.enqueue_job.call_args[0]
    assert call_args[0] == "process_url_job"
    assert call_args[2] == "my prompt"
    assert call_args[3] == "de"


async def test_process_url_missing_prompt_returns_422(api_client):
    resp = await api_client.post(
        "/process-url",
        json={"s3_url": "https://bucket.s3.amazonaws.com/call.mp4"},
    )
    assert resp.status_code == 422
