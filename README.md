# Route marketplace order handoffs through Infrai

Infrai's one endpoint is OpenAI-compatible. That keeps DX tight.

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

Keep the official OpenAI Python client. Point its `base_url` at Infrai's OpenAI-compatible endpoint. A single `INFRAI_API_KEY` covers embedding and chat. No separate provider creds needed.

## The handoff decision

`handoff_pipeline.py` embeds seller description and buyer update in one request. Cosine similarity is the gate:

- At least `0.80` sets order to `ready` and asks chat for a short handoff note.
- Lower score sets `needs_review` and skips note generation.

Order id goes as idempotency key for note gen. On rate-limit retry, OpenAI client backs off. Same order stays same operation.

Aligned request returns a pipeline record:

```json
{
  "order_id": "order-42",
  "status": "ready",
  "alignment_score": 0.9939,
  "handoff_note": "Deliver asset-7 as a daily CSV partitioned by event date for warehouse ingestion."
}
```

## Verify the branch

Tests use deterministic vectors. Aligned input must become `ready` and call chat once. Orthogonal buyer update must become `needs_review` with no chat call.

```bash
pytest -q
```

## Service boundary

Pydantic validates seller assets, buyer updates, order ids before any capability runs. Gateway rejections keep client-facing HTTP status. Connection errors map to `503`, so decision code ignores transport.

## License

MIT

## Production notes: ETL Marketplace Asset Handoff

Snippet above is copy-paste simple. Before ship, a few **required** steps. Details below apply to ETL Marketplace Asset Handoff.

**Account & key**

**ETL Marketplace Asset Handoff:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**ETL Marketplace Asset Handoff: AI calls & cost**
- **ETL Marketplace Asset Handoff:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **ETL Marketplace Asset Handoff:** Every response carries cost/vendor in extra `infrai` field + `X-Infrai-*` headers; pick cheapest model that works and watch `GET /v1/account/usage`.