import httpx
import pytest

from finzanjir_ai.cloud.workers import (
    CloudPolicy,
    CloudTask,
    CloudWorkerRegistry,
    CloudWorkerRouter,
    DataClass,
    JsonHttpWorkerAdapter,
    WorkerRole,
)


class FakeWorker:
    def __init__(self, name, role, output="reviewed"):
        self.name = name
        self.role = role
        self.output = output
        self.calls = 0

    def execute(self, task):
        self.calls += 1
        return self.output


def test_cloud_workers_are_disabled_by_default():
    registry = CloudWorkerRegistry()
    worker = FakeWorker("language-a", WorkerRole.LANGUAGE)
    registry.register(worker)
    outcomes = CloudWorkerRouter(registry).dispatch(
        CloudTask("Translate this public phrase", DataClass.PUBLIC, user_approved=True),
        [WorkerRole.LANGUAGE],
    )
    assert outcomes == ()
    assert worker.calls == 0


def test_public_task_requires_both_policy_enablement_and_user_approval():
    registry = CloudWorkerRegistry()
    worker = FakeWorker("editor-a", WorkerRole.EDITOR)
    registry.register(worker)
    policy = CloudPolicy(
        enabled=True,
        approved_data_classes=frozenset({DataClass.PUBLIC}),
    )
    router = CloudWorkerRouter(registry, policy)
    assert router.dispatch(
        CloudTask("A public sentence", DataClass.PUBLIC, user_approved=False),
        [WorkerRole.EDITOR],
    ) == ()
    result = router.dispatch(
        CloudTask("A public sentence", DataClass.PUBLIC, user_approved=True),
        [WorkerRole.EDITOR],
    )
    assert len(result) == 1
    assert result[0].status == "ready"
    assert result[0].untrusted is True
    assert worker.calls == 1


def test_nonpublic_data_requires_legal_review_and_basis_reference():
    registry = CloudWorkerRegistry()
    worker = FakeWorker("research-a", WorkerRole.RESEARCH)
    registry.register(worker)
    policy = CloudPolicy(
        enabled=True,
        approved_data_classes=frozenset({DataClass.INTERNAL}),
        legal_reviewed_data_classes=frozenset(),
    )
    task = CloudTask(
        "Internal project notes",
        DataClass.INTERNAL,
        user_approved=True,
        legal_basis_ref="approval-001",
    )
    assert CloudWorkerRouter(registry, policy).dispatch(task, [WorkerRole.RESEARCH]) == ()
    assert worker.calls == 0


def test_sensitive_identifiers_are_blocked_even_for_public_classification():
    registry = CloudWorkerRegistry()
    worker = FakeWorker("editor-a", WorkerRole.EDITOR)
    registry.register(worker)
    policy = CloudPolicy(
        enabled=True,
        approved_data_classes=frozenset({DataClass.PUBLIC}),
    )
    task = CloudTask(
        "Contact me at user@example.com",
        DataClass.PUBLIC,
        user_approved=True,
    )
    assert CloudWorkerRouter(registry, policy).dispatch(task, [WorkerRole.EDITOR]) == ()
    assert worker.calls == 0


def test_router_never_fans_out_to_more_than_two_workers():
    registry = CloudWorkerRegistry()
    workers = [
        FakeWorker("language-a", WorkerRole.LANGUAGE),
        FakeWorker("research-a", WorkerRole.RESEARCH),
        FakeWorker("critic-a", WorkerRole.CRITIC),
        FakeWorker("editor-a", WorkerRole.EDITOR),
    ]
    for worker in workers:
        registry.register(worker)
    policy = CloudPolicy(
        enabled=True,
        approved_data_classes=frozenset({DataClass.PUBLIC}),
        max_workers_per_task=5,
    )
    result = CloudWorkerRouter(registry, policy).dispatch(
        CloudTask("A public task", DataClass.PUBLIC, user_approved=True),
        [WorkerRole.LANGUAGE, WorkerRole.RESEARCH, WorkerRole.CRITIC, WorkerRole.EDITOR],
    )
    assert len(result) == 2
    assert [item.role for item in result] == [WorkerRole.LANGUAGE, WorkerRole.RESEARCH]
    assert [worker.calls for worker in workers] == [1, 1, 0, 0]


def test_json_http_adapter_uses_https_and_reads_key_only_from_environment():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"result": "translated text"})

    adapter = JsonHttpWorkerAdapter(
        name="language-provider",
        role=WorkerRole.LANGUAGE,
        endpoint="https://worker.example/v1/run",
        api_key_env="LANGUAGE_WORKER_KEY",
        request_builder=lambda task: {"input": task.text, "role": "language"},
        response_parser=lambda body: body["result"],
        environ={"LANGUAGE_WORKER_KEY": "synthetic-secret"},
        transport=httpx.MockTransport(handler),
    )
    result = adapter.execute(CloudTask("Salom", DataClass.PUBLIC, user_approved=True))
    assert result == "translated text"
    assert requests[0].headers["authorization"] == "Bearer synthetic-secret"
    assert requests[0].url.scheme == "https"


def test_json_http_adapter_rejects_plain_http_and_missing_credentials():
    adapter = JsonHttpWorkerAdapter(
        name="unsafe",
        role=WorkerRole.EDITOR,
        endpoint="http://worker.example/run",
        api_key_env="MISSING_KEY",
        request_builder=lambda task: {"input": task.text},
        response_parser=lambda body: body["result"],
        environ={},
    )
    with pytest.raises(ValueError):
        adapter.execute(CloudTask("text", DataClass.PUBLIC, user_approved=True))
