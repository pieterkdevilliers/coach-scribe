"""Tests for POST /transcribe, /extract, and /process endpoints."""


async def test_transcribe_returns_job_id(api_client, mock_pool):  # noqa: ARG001
    """Successful upload returns a job_id."""
    resp = await api_client.post(
        "/transcribe",
        files={"file": ("audio.wav", b"fake audio data", "audio/wav")},
        data={"language": "en"},
    )
    assert resp.status_code == 200
    assert resp.json()["job_id"] == "test-job-id-123"


async def test_transcribe_enqueues_correct_job(api_client, mock_pool):
    """transcribe_job is enqueued with language, timestamps, and diarize."""
    await api_client.post(
        "/transcribe",
        files={"file": ("audio.mp4", b"fake video data", "video/mp4")},
        data={"language": "fr", "timestamps": "true"},
    )
    mock_pool.enqueue_job.assert_called_once()
    call_args = mock_pool.enqueue_job.call_args[0]
    assert call_args[0] == "transcribe_job"
    assert call_args[2] == "fr"    # language
    assert call_args[3] is True    # timestamps
    assert call_args[4] is True    # diarize default


async def test_transcribe_enqueues_with_diarize(api_client, mock_pool):
    """diarize=true is forwarded to the enqueued job."""
    await api_client.post(
        "/transcribe",
        files={"file": ("audio.wav", b"fake audio", "audio/wav")},
        data={"diarize": "true"},
    )
    call_args = mock_pool.enqueue_job.call_args[0]
    assert call_args[4] is True


async def test_transcribe_missing_file_returns_422(api_client):
    """Missing file field returns HTTP 422."""
    resp = await api_client.post("/transcribe", data={"language": "en"})
    assert resp.status_code == 422


async def test_extract_returns_job_id(api_client, mock_pool):  # noqa: ARG001
    """Successful extract request returns a job_id."""
    resp = await api_client.post(
        "/extract",
        json={"transcript": "hello world", "prompt": "summarise"},
    )
    assert resp.status_code == 200
    assert resp.json()["job_id"] == "test-job-id-123"


async def test_extract_enqueues_correct_job(api_client, mock_pool):
    """extract_job is enqueued with transcript and prompt."""
    await api_client.post(
        "/extract",
        json={"transcript": "the transcript", "prompt": "the prompt"},
    )
    mock_pool.enqueue_job.assert_called_once_with(
        "extract_job", "the transcript", "the prompt"
    )


async def test_extract_missing_transcript_returns_422(api_client):
    """Missing transcript field returns HTTP 422."""
    resp = await api_client.post("/extract", json={"prompt": "summarise"})
    assert resp.status_code == 422


async def test_extract_missing_prompt_returns_422(api_client):
    """Missing prompt field returns HTTP 422."""
    resp = await api_client.post("/extract", json={"transcript": "some text"})
    assert resp.status_code == 422


async def test_process_returns_job_id(api_client, mock_pool):  # noqa: ARG001
    """Successful process upload returns a job_id."""
    resp = await api_client.post(
        "/process",
        files={"file": ("audio.wav", b"fake audio data", "audio/wav")},
        data={"prompt": "summarise this call"},
    )
    assert resp.status_code == 200
    assert resp.json()["job_id"] == "test-job-id-123"


async def test_process_enqueues_correct_job(api_client, mock_pool):
    """process_job is enqueued with file path, prompt, language, and diarize."""
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
    assert call_args[4] is True         # diarize default


async def test_process_enqueues_with_diarize(api_client, mock_pool):
    """diarize=true is forwarded to the enqueued process job."""
    await api_client.post(
        "/process",
        files={"file": ("audio.wav", b"fake audio", "audio/wav")},
        data={"prompt": "summarise", "diarize": "true"},
    )
    call_args = mock_pool.enqueue_job.call_args[0]
    assert call_args[4] is True


async def test_process_missing_prompt_returns_422(api_client):
    """Missing prompt field returns HTTP 422."""
    resp = await api_client.post(
        "/process",
        files={"file": ("audio.wav", b"fake audio data", "audio/wav")},
    )
    assert resp.status_code == 422


async def test_transcribe_url_returns_job_id(api_client, mock_pool):  # noqa: ARG001
    """Presigned URL transcription request returns a job_id."""
    resp = await api_client.post(
        "/transcribe-url",
        json={"s3_url": "https://bucket.s3.amazonaws.com/call.mp4"},
    )
    assert resp.status_code == 200
    assert resp.json()["job_id"] == "test-job-id-123"


async def test_transcribe_url_enqueues_correct_job(api_client, mock_pool):
    """transcribe_url_job is enqueued with url, language, timestamps, and diarize."""
    await api_client.post(
        "/transcribe-url",
        json={"s3_url": "https://bucket.s3.amazonaws.com/call.mp4", "language": "fr"},
    )
    mock_pool.enqueue_job.assert_called_once()
    call_args = mock_pool.enqueue_job.call_args[0]
    assert call_args[0] == "transcribe_url_job"
    assert call_args[1] == "https://bucket.s3.amazonaws.com/call.mp4"
    assert call_args[2] == "fr"
    assert call_args[4] is True   # diarize default


async def test_transcribe_url_enqueues_with_diarize(api_client, mock_pool):
    """diarize=true is forwarded to the enqueued transcribe_url job."""
    await api_client.post(
        "/transcribe-url",
        json={"s3_url": "https://bucket.s3.amazonaws.com/call.mp4", "diarize": True},
    )
    call_args = mock_pool.enqueue_job.call_args[0]
    assert call_args[4] is True


async def test_transcribe_url_missing_url_returns_422(api_client):
    """Missing s3_url field returns HTTP 422."""
    resp = await api_client.post("/transcribe-url", json={"language": "en"})
    assert resp.status_code == 422


async def test_process_url_returns_job_id(api_client, mock_pool):  # noqa: ARG001
    """Presigned URL process request returns a job_id."""
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
    """process_url_job is enqueued with url, prompt, language, and diarize."""
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
    assert call_args[4] is True   # diarize default


async def test_process_url_enqueues_with_diarize(api_client, mock_pool):
    """diarize=true is forwarded to the enqueued process_url job."""
    await api_client.post(
        "/process-url",
        json={
            "s3_url": "https://bucket.s3.amazonaws.com/call.mp4",
            "prompt": "summarise",
            "diarize": True,
        },
    )
    call_args = mock_pool.enqueue_job.call_args[0]
    assert call_args[4] is True


async def test_process_url_missing_prompt_returns_422(api_client):
    """Missing prompt field returns HTTP 422."""
    resp = await api_client.post(
        "/process-url",
        json={"s3_url": "https://bucket.s3.amazonaws.com/call.mp4"},
    )
    assert resp.status_code == 422
