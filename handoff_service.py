"""Typed HTTP boundary for marketplace handoff requests."""

from fastapi import FastAPI, HTTPException
from openai import APIConnectionError, APIStatusError
from pydantic import BaseModel, Field

from handoff_pipeline import BuyerUpdate, HandoffPipeline, SellerAsset


class SellerAssetRequest(BaseModel):
    asset_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    delivery_notes: str = Field(min_length=1)


class BuyerUpdateRequest(BaseModel):
    buyer_id: str = Field(min_length=1)
    requested_outcome: str = Field(min_length=1)


class HandoffRequest(BaseModel):
    order_id: str = Field(min_length=1)
    seller_asset: SellerAssetRequest
    buyer_update: BuyerUpdateRequest


class HandoffResponse(BaseModel):
    order_id: str
    status: str
    alignment_score: float
    handoff_note: str | None


app = FastAPI(title="Marketplace order handoff")


@app.post("/handoffs", response_model=HandoffResponse)
def create_handoff(request: HandoffRequest) -> HandoffResponse:
    pipeline = HandoffPipeline()
    try:
        result = pipeline.build_handoff(
            request.order_id,
            SellerAsset(**request.seller_asset.model_dump()),
            BuyerUpdate(**request.buyer_update.model_dump()),
        )
    except APIStatusError as exc:
        raise HTTPException(status_code=exc.status_code, detail="Gateway request rejected") from exc
    except APIConnectionError as exc:
        raise HTTPException(status_code=503, detail="Gateway connection failed") from exc
    return HandoffResponse(**result.__dict__)
