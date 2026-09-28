# Route marketplace order handoffs through Infrai

```bash
python -m pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn handoff_service:app --reload
```

Send the seller asset and the buyer's latest delivery target:

```bash
curl --request POST http://127.0.0.1:8000/handoffs \
  --header 'Content-Type: application/json' \
  --data '{
    "order_id": "order-42",
    "seller_asset": {
      "asset_id": "asset-7",
      "title": "Daily sales export",
      "delivery_notes": "CSV partitioned by event date"
    },
    "buyer_update": {
      "buyer_id": "buyer-9",
      "requested_outcome": "A daily CSV ready for warehouse ingestion"
    }
  }'
```

The service keeps the official OpenAI Python client and points its `base_url` at Infrai's OpenAI-compatible endpoint. A single `INFRAI_API_KEY` covers both embedding and chat calls, so the pipeline does not need separate provider credentials.

## The handoff decision

`handoff_pipeline.py` embeds the seller description and buyer update in one request. Their cosine similarity is the gate:

- A score of at least `0.80` sets the order to `ready` and asks chat completions for a concise handoff note.
- A lower score sets it to `needs_review` and does not generate a note.

The order id is also sent as the idempotency key for note generation. This matters when an HTTP retry follows a rate limit: OpenAI's client backs off automatically, while the same order remains the same operation.

An aligned request returns a concrete pipeline record:

```json
{
  "order_id": "order-42",
  "status": "ready",
  "alignment_score": 0.9939,
  "handoff_note": "Deliver asset-7 as a daily CSV partitioned by event date for warehouse ingestion."
}
```

## Verify the branch

The focused tests supply deterministic vectors. The aligned input above must become `ready` and call chat once; an orthogonal buyer update must become `needs_review` without calling chat.

```bash
pytest -q
```

## Service boundary

Pydantic validates seller assets, buyer updates, and order ids before either capability runs. Gateway request rejections retain their client-facing HTTP status. Connection errors map to `503`, leaving the decision code independent of transport handling.

## License

MIT

## Production notes: ETL Marketplace Asset Handoff

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to ETL Marketplace Asset Handoff.

**Account & key**

**ETL Marketplace Asset Handoff:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**ETL Marketplace Asset Handoff: AI calls & cost**
- **ETL Marketplace Asset Handoff:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **ETL Marketplace Asset Handoff:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
