# Additional routes for Marketing SaaS - Phases 4-11
# This file contains routes for: Stripe Payments, Company Profiles, Metrics, AI Tools, Tasks, Strategies

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
import os

# Pydantic Models for Additional Features

# Stripe Payment Models
class CheckoutRequest(BaseModel):
    package_id: str
    user_count: int = 5
    origin_url: str

class PaymentStatusRequest(BaseModel):
    session_id: str

# Company Profile Models
class CompanyProfileCreate(BaseModel):
    company_name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None

class SocialMediaProfile(BaseModel):
    platform: str  # facebook, instagram, linkedin, twitter, tiktok, youtube
    url: str
    followers: Optional[int] = 0

# Marketing Metrics Models
class MetricEntry(BaseModel):
    metric_type: str  # traffic, keywords, backlinks, domain_authority, engagement
    value: float
    date: str
    notes: Optional[str] = None

# AI Assessment Models
class AssessmentRequest(BaseModel):
    workspace_id: str
    include_recommendations: bool = True

# Strategy Models
class StrategyCreate(BaseModel):
    title: str
    description: str
    template_id: Optional[str] = None
    use_ai: bool = False

# Task Models
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: str = "medium"  # low, medium, high
    due_date: Optional[str] = None
    status: str = "todo"  # todo, in_progress, completed, blocked

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None

# AI Creative Tools Models
class CopywriterRequest(BaseModel):
    content_type: str  # blog, social_media, email, ad_copy
    topic: str
    tone: str = "professional"  # professional, casual, friendly, formal
    length: str = "medium"  # short, medium, long

class AdCreatorRequest(BaseModel):
    product_name: str
    target_audience: str
    platform: str  # facebook, instagram, google_ads
    goal: str  # awareness, conversion, engagement

class GraphicsRequest(BaseModel):
    prompt: str
    style: str = "modern"  # modern, minimal, vibrant, professional
    provider: str = "openai"  # openai or gemini
