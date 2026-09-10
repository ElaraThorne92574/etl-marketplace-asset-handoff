from types import SimpleNamespace

from handoff_pipeline import BuyerUpdate, HandoffPipeline, SellerAsset


class FakeEmbeddings:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.vectors = vectors

    def create(self, **request: object) -> SimpleNamespace:
        assert request == {
            "model": "auto",
            "input": [
                "Daily sales export\nCSV partitioned by event date",
                "A daily CSV ready for warehouse ingestion",
            ],
        }
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=value) for value in self.vectors]
        )


class FakeCompletions:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **request: object) -> SimpleNamespace:
        self.calls += 1
        assert request["model"] == "auto"
        assert request["extra_headers"] == {"Idempotency-Key": "order-42"}
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Deliver asset-7 as a daily CSV."))]
        )


class FakeClient:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.embeddings = FakeEmbeddings(vectors)
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


def request_handoff(client: FakeClient):
    return HandoffPipeline(client=client).build_handoff(
        "order-42",
        SellerAsset("asset-7", "Daily sales export", "CSV partitioned by event date"),
        BuyerUpdate("buyer-9", "A daily CSV ready for warehouse ingestion"),
    )


def test_aligned_order_moves_to_ready_and_gets_a_note() -> None:
    client = FakeClient([[1.0, 0.0], [0.9, 0.1]])

    result = request_handoff(client)

    assert result.status == "ready"
    assert result.handoff_note == "Deliver asset-7 as a daily CSV."
    assert client.completions.calls == 1


def test_misaligned_order_stops_for_review_before_chat() -> None:
    client = FakeClient([[1.0, 0.0], [0.0, 1.0]])

    result = request_handoff(client)

    assert result.status == "needs_review"
    assert result.handoff_note is None
    assert client.completions.calls == 0
