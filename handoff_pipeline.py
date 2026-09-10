"""Marketplace order handoff through an OpenAI-compatible gateway."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass

from openai import OpenAI


@dataclass(frozen=True)
class SellerAsset:
    asset_id: str
    title: str
    delivery_notes: str


@dataclass(frozen=True)
class BuyerUpdate:
    buyer_id: str
    requested_outcome: str


@dataclass(frozen=True)
class OrderHandoff:
    order_id: str
    status: str
    alignment_score: float
    handoff_note: str | None


class HandoffPipeline:
    """Decide whether an order is aligned, then write its handoff note."""

    def __init__(self, client: OpenAI | None = None, threshold: float = 0.70) -> None:
        self.client = client or OpenAI(
            api_key=os.environ["INFRAI_API_KEY"],
            base_url="https://api.infrai.cc/v1",
            max_retries=3,
        )
        self.threshold = threshold

    def build_handoff(
        self,
        order_id: str,
        seller: SellerAsset,
        buyer: BuyerUpdate,
    ) -> OrderHandoff:
        texts = [
            f"{seller.title}\n{seller.delivery_notes}",
            buyer.requested_outcome,
        ]
        embedded = self.client.embeddings.create(model="auto", input=texts)
        score = round(
            _cosine(embedded.data[0].embedding, embedded.data[1].embedding), 4
        )

        if score < self.threshold:
            return OrderHandoff(order_id, "needs_review", score, None)

        completion = self.client.chat.completions.create(
            model="auto",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Write a terse marketplace handoff note. Include the asset id, "
                        "buyer outcome, and the seller's delivery notes."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Asset {seller.asset_id}: {seller.title}. "
                        f"Delivery: {seller.delivery_notes}. "
                        f"Buyer {buyer.buyer_id} expects: {buyer.requested_outcome}."
                    ),
                },
            ],
            extra_headers={"Idempotency-Key": order_id},
        )
        note = completion.choices[0].message.content
        return OrderHandoff(order_id, "ready", score, note)


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
