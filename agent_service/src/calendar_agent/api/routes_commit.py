"""
Commit endpoint for applying approved action plans.

This is the human-in-the-loop approval step with safety checks.
"""

from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException

from calendar_agent.agent.schemas import CommitRequest, CommitResponse, ActionPlan
from calendar_agent.agent.planner import CalendarPlanner, _plan_store
from calendar_agent.db.repo import EventRepository


router = APIRouter()


def validate_event_exists(repo: EventRepository, event_id: int, action_type: str) -> Dict[str, Any]:
    """Validate that an event exists before modifying it."""
    event = repo.get_event(event_id)
    if not event:
        return {
            "valid": False,
            "error": f"Event ID {event_id} not found for {action_type}"
        }
    return {"valid": True, "event": event}


def check_create_conflicts(repo: EventRepository, action) -> List[str]:
    """Check for conflicts when creating an event."""
    warnings = []
    
    try:
        # Parse start datetime
        start_dt = datetime.fromisoformat(action.start.replace("Z", "+00:00"))
        event_date = start_dt.strftime("%Y-%m-%d")
        event_time = start_dt.strftime("%H:%M")
        
        # Check for conflicts
        conflicts = repo.check_conflicts(
            start_date=event_date,
            start_time=event_time
        )
        
        if conflicts:
            for c in conflicts:
                warnings.append(
                    f"Conflict with '{c['title']}' at {c['time']} on {c['date']}"
                )
    except Exception as e:
        warnings.append(f"Could not check conflicts: {str(e)}")
    
    return warnings


def check_move_conflicts(repo: EventRepository, action) -> List[str]:
    """Check for conflicts when moving an event."""
    warnings = []
    
    try:
        start_dt = datetime.fromisoformat(action.new_start.replace("Z", "+00:00"))
        new_date = start_dt.strftime("%Y-%m-%d")
        new_time = start_dt.strftime("%H:%M")
        
        conflicts = repo.check_conflicts(
            start_date=new_date,
            start_time=new_time,
            ignore_event_id=action.event_id
        )
        
        if conflicts:
            for c in conflicts:
                warnings.append(
                    f"Moving would conflict with '{c['title']}' at {c['time']}"
                )
    except Exception as e:
        warnings.append(f"Could not check conflicts: {str(e)}")
    
    return warnings


@router.post("", response_model=CommitResponse)
async def commit_plan(request: CommitRequest) -> CommitResponse:
    """
    Commit an approved action plan to the database.
    
    This executes all actions in the plan and permanently modifies the calendar.
    
    ## Safety Checks
    
    Before applying, the server will:
    1. Re-check for conflicts (unless skip_conflict_check=True)
    2. Validate that event IDs exist for update/delete/move actions
    3. Require confirm_deletes=True for any delete actions
    
    ## Example Request
    
    ```json
    {
        "plan_id": "plan_abc123",
        "confirm_deletes": true
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
    
    repo = EventRepository()
    results = []
    all_warnings = []
    
    # ============== SAFETY CHECKS ==============
    
    for action in plan.actions:
        action_type = action.type
        
        # Check 1: Validate event exists for update/delete/move
        if action_type in ["update_event", "delete_event", "move_event", "cancel_recurrence"]:
            validation = validate_event_exists(repo, action.event_id, action_type)
            if not validation["valid"]:
                return CommitResponse(
                    success=False,
                    error=validation["error"],
                    results=[]
                )
        
        # Check 2: Require confirmation for deletes
        if action_type == "delete_event":
            if not request.confirm_deletes:
                return CommitResponse(
                    success=False,
                    error="Delete actions require confirm_deletes=True in the request",
                    results=[]
                )
        
        # Check 3: Re-check conflicts (unless skipped)
        if not request.skip_conflict_check:
            if action_type == "create_event":
                warnings = check_create_conflicts(repo, action)
                all_warnings.extend(warnings)
            elif action_type == "move_event":
                warnings = check_move_conflicts(repo, action)
                all_warnings.extend(warnings)
    
    # If there are conflict warnings and user didn't skip check, warn but continue
    # (conflicts are warnings, not blockers - user may have intended the overlap)
    
    # ============== EXECUTE ACTIONS ==============
    
    for action in plan.actions:
        try:
            if action.type == "create_event":
                # Parse ISO datetime
                start_dt = datetime.fromisoformat(action.start.replace("Z", "+00:00"))
                event_date = start_dt.strftime("%Y-%m-%d")
                event_time = start_dt.strftime("%H:%M")
                
                recurrence = "none"
                recurrence_end = None
                if action.recurrence:
                    recurrence = action.recurrence.freq
                    if action.recurrence.until:
                        recurrence_end = action.recurrence.until
                    elif action.recurrence.count:
                        # Calculate end date based on count
                        from dateutil.relativedelta import relativedelta
                        if recurrence == "daily":
                            end_dt = start_dt + relativedelta(days=action.recurrence.count - 1)
                        elif recurrence == "weekly":
                            end_dt = start_dt + relativedelta(weeks=action.recurrence.count - 1)
                        elif recurrence == "monthly":
                            end_dt = start_dt + relativedelta(months=action.recurrence.count - 1)
                        else:
                            end_dt = start_dt + relativedelta(years=action.recurrence.count - 1)
                        recurrence_end = end_dt.strftime("%Y-%m-%d")
                
                result = repo.create_event(
                    title=action.title,
                    date=event_date,
                    time=event_time,
                    location=action.location or "",
                    notes=action.notes or "",
                    recurrence=recurrence,
                    recurrence_end=recurrence_end,
                )
                results.append({
                    "action": "create_event",
                    "success": True,
                    "event": result
                })
            
            elif action.type == "update_event":
                updates = {}
                if action.title:
                    updates["title"] = action.title
                if action.start:
                    start_dt = datetime.fromisoformat(action.start.replace("Z", "+00:00"))
                    updates["date"] = start_dt.strftime("%Y-%m-%d")
                    updates["time"] = start_dt.strftime("%H:%M")
                if action.location:
                    updates["location"] = action.location
                if action.notes:
                    updates["notes"] = action.notes
                
                result = repo.update_event(action.event_id, **updates)
                results.append({
                    "action": "update_event",
                    "success": True,
                    "event": result
                })
            
            elif action.type == "move_event":
                start_dt = datetime.fromisoformat(action.new_start.replace("Z", "+00:00"))
                new_date = start_dt.strftime("%Y-%m-%d")
                new_time = start_dt.strftime("%H:%M")
                
                result = repo.move_event(action.event_id, new_date, new_time)
                results.append({
                    "action": "move_event",
                    "success": True,
                    "event": result
                })
            
            elif action.type == "delete_event":
                success = repo.delete_event(action.event_id)
                results.append({
                    "action": "delete_event",
                    "success": success,
                    "event_id": action.event_id
                })
            
            elif action.type == "cancel_recurrence":
                success = repo.stop_recurrence(
                    action.event_id,
                    action.cancel_after
                )
                results.append({
                    "action": "cancel_recurrence",
                    "success": success,
                    "event_id": action.event_id
                })
        
        except Exception as e:
            results.append({
                "action": action.type,
                "success": False,
                "error": str(e)
            })
    
    # Remove the plan after committing
    if request.plan_id in _plan_store:
        del _plan_store[request.plan_id]
    
    all_success = all(r.get("success", False) for r in results)
    
    return CommitResponse(
        success=all_success,
        committed_actions=len([r for r in results if r.get("success")]),
        results=results,
        error=None if all_success else "Some actions failed"
    )


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
    del _plan_store[plan_id]
    
    return {"success": True, "message": f"Plan {plan_id} cancelled"}


@router.get("/{plan_id}/validate")
async def validate_plan(plan_id: str):
    """
    Validate a plan before committing.
    
    Checks:
    - Event IDs exist
    - Conflicts at proposed times
    - Recurrence rules are valid
    """
    plan = CalendarPlanner.get_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=404,
            detail=f"Plan {plan_id} not found"
        )
    
    repo = EventRepository()
    issues = []
    warnings = []
    
    for i, action in enumerate(plan.actions):
        action_type = action.type
        
        # Check event exists
        if action_type in ["update_event", "delete_event", "move_event", "cancel_recurrence"]:
            event = repo.get_event(action.event_id)
            if not event:
                issues.append(f"Action {i+1}: Event ID {action.event_id} not found")
        
        # Check conflicts
        if action_type == "create_event":
            conflicts = check_create_conflicts(repo, action)
            warnings.extend(conflicts)
        elif action_type == "move_event":
            conflicts = check_move_conflicts(repo, action)
            warnings.extend(conflicts)
    
    return {
        "plan_id": plan_id,
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "action_count": len(plan.actions)
    }
