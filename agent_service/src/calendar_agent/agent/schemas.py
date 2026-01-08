"""
Pydantic schemas for agent input/output.

Defines the structured action plan format that the agent returns.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# ==================== Action Types ====================

class RecurrenceRule(BaseModel):
    """Recurrence rule for repeating events."""
    freq: Literal["daily", "weekly", "monthly", "yearly"] = Field(
        description="Frequency of recurrence"
    )
    interval: int = Field(default=1, description="Interval between occurrences")
    count: Optional[int] = Field(default=None, description="Number of occurrences")
    until: Optional[str] = Field(default=None, description="End date (YYYY-MM-DD)")
    byweekday: Optional[List[str]] = Field(
        default=None,
        description="Days of week (MO, TU, WE, TH, FR, SA, SU)"
    )


class CreateEventAction(BaseModel):
    """Action to create a new event."""
    type: Literal["create_event"] = "create_event"
    title: str = Field(description="Event title")
    start: str = Field(description="Start datetime (ISO 8601 format)")
    end: Optional[str] = Field(default=None, description="End datetime (ISO 8601 format)")
    location: Optional[str] = Field(default=None, description="Event location")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    recurrence: Optional[RecurrenceRule] = Field(default=None, description="Recurrence rule")


class UpdateEventAction(BaseModel):
    """Action to update an existing event."""
    type: Literal["update_event"] = "update_event"
    event_id: int = Field(description="ID of event to update")
    title: Optional[str] = Field(default=None, description="New title")
    start: Optional[str] = Field(default=None, description="New start datetime")
    end: Optional[str] = Field(default=None, description="New end datetime")
    location: Optional[str] = Field(default=None, description="New location")
    notes: Optional[str] = Field(default=None, description="New notes")


class MoveEventAction(BaseModel):
    """Action to move an event to a new date/time."""
    type: Literal["move_event"] = "move_event"
    event_id: int = Field(description="ID of event to move")
    new_start: str = Field(description="New start datetime (ISO 8601 format)")
    new_end: Optional[str] = Field(default=None, description="New end datetime")
    reason: Optional[str] = Field(default=None, description="Reason for move")


class DeleteEventAction(BaseModel):
    """Action to delete an event."""
    type: Literal["delete_event"] = "delete_event"
    event_id: int = Field(description="ID of event to delete")
    reason: Optional[str] = Field(default=None, description="Reason for deletion")


class CancelRecurrenceAction(BaseModel):
    """Action to stop a recurring event."""
    type: Literal["cancel_recurrence"] = "cancel_recurrence"
    event_id: int = Field(description="ID of recurring event")
    cancel_after: Optional[str] = Field(
        default=None,
        description="Cancel occurrences after this date"
    )


# Union type for all actions
Action = CreateEventAction | UpdateEventAction | MoveEventAction | DeleteEventAction | CancelRecurrenceAction


# ==================== Plan Schema ====================

class ActionPlan(BaseModel):
    """
    A structured plan of calendar actions proposed by the agent.
    
    This is returned to the user for approval before committing.
    """
    plan_id: str = Field(description="Unique identifier for this plan")
    summary: str = Field(description="Human-readable summary of the plan")
    actions: List[Action] = Field(default_factory=list, description="List of actions to perform")
    warnings: List[str] = Field(default_factory=list, description="Any warnings or conflicts")
    needs_approval: bool = Field(default=True, description="Whether user approval is needed")
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="When the plan was created"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


# ==================== API Request/Response Schemas ====================

class ChatRequest(BaseModel):
    """Request body for the /chat endpoint."""
    message: str = Field(description="Natural language calendar command")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context (e.g., timezone, user preferences)"
    )


class ChatResponse(BaseModel):
    """Response body for the /chat endpoint."""
    success: bool = Field(description="Whether the request was successful")
    plan: Optional[ActionPlan] = Field(default=None, description="Proposed action plan")
    message: Optional[str] = Field(default=None, description="Response message")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class CommitRequest(BaseModel):
    """Request body for the /commit endpoint."""
    plan_id: str = Field(description="ID of the plan to commit")
    modifications: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Any modifications to the plan before committing"
    )


class CommitResponse(BaseModel):
    """Response body for the /commit endpoint."""
    success: bool = Field(description="Whether the commit was successful")
    committed_actions: int = Field(default=0, description="Number of actions committed")
    results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Results of each action"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")


# ==================== Event Schema (for API) ====================

class EventCreate(BaseModel):
    """Schema for creating an event via REST API."""
    title: str
    date: str
    time: str
    end_time: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    recurrence: str = "none"
    recurrence_end: Optional[str] = None


class EventUpdate(BaseModel):
    """Schema for updating an event via REST API."""
    title: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    recurrence: Optional[str] = None
    recurrence_end: Optional[str] = None


class EventResponse(BaseModel):
    """Schema for event response."""
    id: int
    title: str
    date: str
    time: str
    end_time: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    recurrence: str
    recurrence_end: Optional[str] = None

