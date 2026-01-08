"""
Commit endpoint for applying approved action plans.

This is the human-in-the-loop approval step.
"""

from fastapi import APIRouter, HTTPException

from calendar_agent.agent.schemas import CommitRequest, CommitResponse
from calendar_agent.agent.planner import CalendarPlanner


router = APIRouter()


@router.post("", response_model=CommitResponse)
async def commit_plan(request: CommitRequest) -> CommitResponse:
    """
    Commit an approved action plan to the database.
    
    This executes all actions in the plan and permanently modifies the calendar.
    
    ## Example Request
    
    ```json
    {
        "plan_id": "plan_abc123"
    }
    ```
    
    ## Example Response
    
    ```json
    {
        "success": true,
        "committed_actions": 1,
        "results": [
            {
                "action": "create_event",
                "success": true,
                "event": {...}
            }
        ]
    }
    ```
    """
    # Verify plan exists
    plan = CalendarPlanner.get_plan(request.plan_id)
    if not plan:
        raise HTTPException(
            status_code=404,
            detail=f"Plan {request.plan_id} not found. It may have expired or been committed already."
        )
    
    # Apply modifications if provided
    if request.modifications:
        # TODO: Apply modifications to plan
        pass
    
    # Commit the plan
    try:
        result = CalendarPlanner.commit_plan(request.plan_id)
        return CommitResponse(
            success=result.get("success", False),
            committed_actions=result.get("committed_actions", 0),
            results=result.get("results", []),
            error=result.get("error"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{plan_id}")
async def cancel_plan(plan_id: str):
    """
    Cancel/discard a plan without committing.
    
    Use this to reject a proposed plan.
    """
    plan = CalendarPlanner.get_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=404,
            detail=f"Plan {plan_id} not found"
        )
    
    # Remove from store
    from calendar_agent.agent.planner import _plan_store
    del _plan_store[plan_id]
    
    return {"success": True, "message": f"Plan {plan_id} cancelled"}

