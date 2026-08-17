"""
Contact and enquiry API routes.

POST /api/contact  — general contact form
POST /api/enquiry  — product / showroom enquiry

Both accept JSON and return JSON. Data is stored in SQLite via database.db.
"""

from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from database.db import insert_contact_message, insert_enquiry, insert_review

router = APIRouter(prefix="/api", tags=["enquiry"])

# Basic phone: digits, spaces, +, -, parentheses; 7–20 chars of substance
_PHONE_RE = re.compile(r"^[\d\s+\-().]{7,20}$")
_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ContactRequest(BaseModel):
    """Payload for the general contact form."""

    name: str = Field(..., min_length=2, max_length=120)
    phone: str = Field(..., min_length=7, max_length=40)
    email: str = Field(..., min_length=5, max_length=180)
    message: str = Field(..., min_length=10, max_length=5000)

    @field_validator("name", "phone", "email", "message")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not _PHONE_RE.match(value):
            raise ValueError("Please enter a valid phone number")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not _EMAIL_RE.match(value):
            raise ValueError("Please enter a valid email address")
        return value.lower()


class EnquiryRequest(BaseModel):
    """Payload for product / showroom enquiries."""

    name: str = Field(..., min_length=2, max_length=120)
    phone: str = Field(..., min_length=7, max_length=40)
    email: str = Field(..., min_length=5, max_length=180)
    message: str = Field(..., min_length=10, max_length=5000)
    product_name: Optional[str] = Field(default=None, max_length=200)
    product_category: Optional[str] = Field(default=None, max_length=100)

    @field_validator("name", "phone", "email", "message")
    @classmethod
    def strip_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned

    @field_validator("product_name", "product_category")
    @classmethod
    def strip_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not _PHONE_RE.match(value):
            raise ValueError("Please enter a valid phone number")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not _EMAIL_RE.match(value):
            raise ValueError("Please enter a valid email address")
        return value.lower()


class ApiSuccessResponse(BaseModel):
    """Standard success envelope."""

    success: bool = True
    message: str
    id: Optional[int] = None


class ApiErrorResponse(BaseModel):
    """Standard error envelope (documentation / consistency)."""

    success: bool = False
    message: str
    detail: Optional[str] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/contact",
    response_model=ApiSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit contact form",
    responses={
        422: {"description": "Validation error"},
        500: {"model": ApiErrorResponse, "description": "Server error"},
    },
)
async def submit_contact(payload: ContactRequest) -> ApiSuccessResponse:
    """
    Accept a general contact form submission and store it in SQLite.
    """
    try:
        row_id = insert_contact_message(
            name=payload.name,
            phone=payload.phone,
            email=payload.email,
            message=payload.message,
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save your message. Please try again later.",
        ) from exc

    return ApiSuccessResponse(
        success=True,
        message="Thank you! Your message has been received. We will contact you shortly.",
        id=row_id,
    )


class ReviewRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    message: str = Field(..., min_length=10, max_length=3000)
    rating: int = Field(default=5, ge=1, le=5)
    email: Optional[str] = Field(default=None, max_length=180)
    phone: Optional[str] = Field(default=None, max_length=40)
    title: Optional[str] = Field(default=None, max_length=200)

    @field_validator("name", "message")
    @classmethod
    def strip_req(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned

    @field_validator("email", "phone", "title")
    @classmethod
    def strip_opt(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


@router.post(
    "/review",
    response_model=ApiSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit customer review / rating",
)
async def submit_review(payload: ReviewRequest) -> ApiSuccessResponse:
    try:
        row_id = insert_review(
            name=payload.name,
            message=payload.message,
            rating=payload.rating,
            email=payload.email,
            phone=payload.phone,
            title=payload.title,
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save your review. Please try again later.",
        ) from exc
    return ApiSuccessResponse(
        success=True,
        message="Thank you! Your review was submitted and will appear after admin approval.",
        id=row_id,
    )


@router.post(
    "/enquiry",
    response_model=ApiSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit product / showroom enquiry",
    responses={
        422: {"description": "Validation error"},
        500: {"model": ApiErrorResponse, "description": "Server error"},
    },
)
async def submit_enquiry(payload: EnquiryRequest) -> ApiSuccessResponse:
    """
    Accept a product or showroom enquiry and store it in SQLite.
    """
    try:
        row_id = insert_enquiry(
            name=payload.name,
            phone=payload.phone,
            email=payload.email,
            message=payload.message,
            product_name=payload.product_name,
            product_category=payload.product_category,
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save your enquiry. Please try again later.",
        ) from exc

    return ApiSuccessResponse(
        success=True,
        message="Thank you! Your enquiry has been submitted. Our team will reach out soon.",
        id=row_id,
    )
