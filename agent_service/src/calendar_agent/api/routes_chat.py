"""
Chat endpoint for natural language calendar commands.

This is the main entry point for the AI agent.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from calendar_agent.agent.schemas import ChatRequest, ChatResponse, ActionPlan
from calendar_agent.agent.planner import CalendarPlanner


router = APIRouter()

# Singleton planner instance
_planner: Optional[CalendarPlanner] = None


def get_planner() -> CalendarPlanner:
    """Get or create the planner instance."""
    global _planner
    if _planner is None:
        _planner = CalendarPlanner()
    return _planner


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a natural language calendar command.
    
    The agent will analyze the request, use tools to gather information,
    and return a structured action plan for approval.
    
    ## Example Request
    
    ```json
    {
        "message": "Add soccer every Tuesday at 6pm for 8 weeks"
    }
    ```
    
    ## Example Response
    
    ```json
    {
        "success": true,
        "plan": {
            "plan_id": "plan_abc123",
            "summary": "I'll create a recurring soccer event...",
            "actions": [
                {
                    "type": "create_event",
                    "title": "Soccer",
                    "start": "2025-01-07T18:00:00",
                    "recurrence": {"freq": "weekly", "count": 8}
                }
            ],
            "warnings": [],
            "needs_approval": true
        }
    }
    ```
    
    After reviewing the plan, use the `/commit` endpoint to apply changes.
    """
    planner = get_planner()
    
    try:
        response = await planner.process_message(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plan/{plan_id}", response_model=ActionPlan)
async def get_plan(plan_id: str) -> ActionPlan:
    """
    Retrieve a previously created action plan.
    
    Plans are stored temporarily until committed or they expire.
    """
    plan = CalendarPlanner.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    return plan


@router.post("/simple", response_model=ChatResponse)
async def chat_simple(message: str) -> ChatResponse:
    """
    Simple chat endpoint that accepts message as query parameter.
    
    Useful for quick testing:
    ```
    POST /chat/simple?message=Add meeting tomorrow at 2pm
    ```
    """
    request = ChatRequest(message=message)
    planner = get_planner()
    
    try:
        response = await planner.process_message(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

