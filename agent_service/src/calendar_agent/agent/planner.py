"""
Calendar Planner - Orchestrates the LLM agent with tools.

This module handles the conversation with the LLM and coordinates tool usage.
"""

import json
import uuid
import re
from datetime import datetime, date
from typing import Optional, Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from calendar_agent.config import settings
from calendar_agent.agent.schemas import (
    ActionPlan, Action, CreateEventAction, UpdateEventAction,
    MoveEventAction, DeleteEventAction, ChatRequest, ChatResponse
)
from calendar_agent.agent.system_prompt import get_system_prompt_with_context
from calendar_agent.tools.event_tools import (
    create_event_tool, update_event_tool, delete_event_tool,
    list_events_tool, search_events_tool, move_event_tool
)
from calendar_agent.tools.conflict_tools import (
    check_conflicts_tool, get_free_slots_tool, find_crunch_days_tool,
    get_day_summary_tool
)
from calendar_agent.tools.time_tools import (
    parse_datetime_tool, get_next_weekday_tool, expand_recurrence_tool,
    get_date_range_tool
)
from calendar_agent.db.repo import EventRepository


# In-memory plan storage (use Redis/DB in production)
_plan_store: Dict[str, ActionPlan] = {}


class CalendarPlanner:
    """
    Orchestrates the calendar agent.
    
    Takes natural language input, uses LLM with tools to understand intent,
    and returns a structured action plan.
    """
    
    def __init__(self):
        """Initialize the planner with LLM and tools."""
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            openai_api_key=settings.openai_api_key,
        )
        
        # Define available tools
        self.tools = [
            # Event tools
            list_events_tool,
            search_events_tool,
            # Conflict tools
            check_conflicts_tool,
            get_free_slots_tool,
            find_crunch_days_tool,
            get_day_summary_tool,
            # Time tools
            parse_datetime_tool,
            get_next_weekday_tool,
            expand_recurrence_tool,
            get_date_range_tool,
        ]
        
        self.repo = EventRepository()
    
    def _create_agent(self, system_prompt: str):
        """Create a React agent with the given system prompt."""
        return create_react_agent(
            self.llm,
            self.tools,
            prompt=system_prompt,
        )
    
    def _generate_plan_id(self) -> str:
        """Generate a unique plan ID."""
        return f"plan_{uuid.uuid4().hex[:12]}"
    
    def _parse_agent_response(self, messages: List, tool_calls: List) -> ActionPlan:
        """
        Parse the agent's response into a structured action plan.
        
        This analyzes the tool calls and agent output to construct the plan.
        """
        plan_id = self._generate_plan_id()
        actions = []
        warnings = []
        
        # Get the final response
        response = ""
        for msg in reversed(messages):
            if hasattr(msg, 'content') and msg.content:
                response = msg.content
                break
        
        # Analyze tool calls for conflicts
        for call in tool_calls:
            if call.get("name") == "check_conflicts_tool":
                result = call.get("result", {})
                if isinstance(result, dict) and result.get("has_conflicts"):
                    conflicts = result.get("conflicts", [])
                    for conflict in conflicts:
                        warnings.append(
                            f"Conflict with '{conflict.get('title')}' at {conflict.get('time')}"
                        )
        
        # Parse the final response for action intent
        response_lower = response.lower()
        
        # Detect create intent
        if any(word in response_lower for word in ["create", "add", "schedule", "new event"]):
            action = self._extract_create_action(response, tool_calls)
            if action:
                actions.append(action)
        
        # Detect move intent
        if any(word in response_lower for word in ["move", "reschedule", "postpone"]):
            action = self._extract_move_action(response, tool_calls)
            if action:
                actions.append(action)
        
        # Detect delete intent
        if any(word in response_lower for word in ["delete", "cancel", "remove"]):
            action = self._extract_delete_action(response, tool_calls)
            if action:
                actions.append(action)
        
        # Determine if approval is needed
        needs_approval = len(actions) > 0
        
        plan = ActionPlan(
            plan_id=plan_id,
            summary=response,
            actions=actions,
            warnings=warnings,
            needs_approval=needs_approval,
            metadata={
                "tool_calls": len(tool_calls),
                "model": settings.llm_model,
            }
        )
        
        # Store the plan
        _plan_store[plan_id] = plan
        
        return plan
    
    def _extract_create_action(self, response: str, tool_calls: List) -> Optional[CreateEventAction]:
        """Extract create event action from agent response."""
        parsed_date = None
        parsed_time = None
        
        for call in tool_calls:
            result = call.get("result", {})
            if call.get("name") == "parse_datetime_tool" and isinstance(result, dict):
                parsed_date = result.get("date")
                parsed_time = result.get("time")
            elif call.get("name") == "get_next_weekday_tool" and isinstance(result, dict):
                parsed_date = result.get("date")
        
        if not parsed_date:
            parsed_date = date.today().isoformat()
        if not parsed_time:
            parsed_time = "09:00"
        
        # Try to extract title from response
        title = "New Event"
        
        # Look for quoted text as title
        quotes = re.findall(r'"([^"]+)"', response)
        if quotes:
            title = quotes[0]
        elif "soccer" in response.lower():
            title = "Soccer"
        elif "meeting" in response.lower():
            title = "Meeting"
        elif "dentist" in response.lower():
            title = "Dentist"
        
        return CreateEventAction(
            title=title,
            start=f"{parsed_date}T{parsed_time}:00",
            end=None,
            location=None,
            notes=None,
            recurrence=None,
        )
    
    def _extract_move_action(self, response: str, tool_calls: List) -> Optional[MoveEventAction]:
        """Extract move event action from agent response."""
        event_id = None
        new_date = None
        
        for call in tool_calls:
            result = call.get("result", {})
            if call.get("name") == "search_events_tool" and isinstance(result, dict):
                events = result.get("events", [])
                if events:
                    event_id = events[0].get("id")
            elif call.get("name") in ["parse_datetime_tool", "get_next_weekday_tool"]:
                if isinstance(result, dict):
                    new_date = result.get("date")
        
        if event_id and new_date:
            return MoveEventAction(
                event_id=event_id,
                new_start=f"{new_date}T09:00:00",
            )
        
        return None
    
    def _extract_delete_action(self, response: str, tool_calls: List) -> Optional[DeleteEventAction]:
        """Extract delete event action from agent response."""
        event_id = None
        
        for call in tool_calls:
            result = call.get("result", {})
            if call.get("name") == "search_events_tool" and isinstance(result, dict):
                events = result.get("events", [])
                if events:
                    event_id = events[0].get("id")
        
        if event_id:
            return DeleteEventAction(
                event_id=event_id,
                reason="User requested deletion",
            )
        
        return None
    
    async def process_message(self, request: ChatRequest) -> ChatResponse:
        """
        Process a natural language message and return an action plan.
        
        Args:
            request: Chat request with the user's message
        
        Returns:
            ChatResponse with proposed action plan or information
        """
        try:
            # Get current date for context
            current_date = date.today().isoformat()
            timezone = request.context.get("timezone", settings.default_timezone) if request.context else settings.default_timezone
            
            # Create system prompt with context
            system_prompt = get_system_prompt_with_context(current_date, timezone)
            
            # Create agent
            agent = self._create_agent(system_prompt)
            
            # Run the agent
            result = await agent.ainvoke({
                "messages": [HumanMessage(content=request.message)]
            })
            
            # Extract messages and tool calls
            messages = result.get("messages", [])
            
            # Collect tool call info from messages
            tool_calls = []
            for msg in messages:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_calls.append({
                            "name": tc.get("name"),
                            "args": tc.get("args", {}),
                        })
                # Also check for tool messages with results
                if hasattr(msg, 'name') and hasattr(msg, 'content'):
                    # This is a ToolMessage
                    tool_calls.append({
                        "name": msg.name,
                        "result": msg.content if isinstance(msg.content, dict) else {"raw": msg.content},
                    })
            
            # Get final response
            output = ""
            for msg in reversed(messages):
                if hasattr(msg, 'content') and isinstance(msg.content, str) and msg.content:
                    output = msg.content
                    break
            
            # Parse response into action plan
            plan = self._parse_agent_response(messages, tool_calls)
            
            return ChatResponse(
                success=True,
                plan=plan,
                message=output,
            )
            
        except Exception as e:
            return ChatResponse(
                success=False,
                error=str(e),
            )
    
    def process_message_sync(self, request: ChatRequest) -> ChatResponse:
        """Synchronous version of process_message."""
        import asyncio
        return asyncio.run(self.process_message(request))
    
    @staticmethod
    def get_plan(plan_id: str) -> Optional[ActionPlan]:
        """Retrieve a stored plan by ID."""
        return _plan_store.get(plan_id)
    
    @staticmethod
    def commit_plan(plan_id: str) -> Dict[str, Any]:
        """
        Commit a plan to the database.
        
        Executes all actions in the plan.
        """
        plan = _plan_store.get(plan_id)
        if not plan:
            return {"success": False, "error": f"Plan {plan_id} not found"}
        
        repo = EventRepository()
        results = []
        
        for action in plan.actions:
            try:
                if action.type == "create_event":
                    # Parse ISO datetime
                    start_dt = datetime.fromisoformat(action.start.replace("Z", "+00:00"))
                    event_date = start_dt.strftime("%Y-%m-%d")
                    event_time = start_dt.strftime("%H:%M")
                    
                    end_time = None
                    if action.end:
                        end_dt = datetime.fromisoformat(action.end.replace("Z", "+00:00"))
                        end_time = end_dt.strftime("%H:%M")
                    
                    recurrence = "none"
                    recurrence_end = None
                    if action.recurrence:
                        recurrence = action.recurrence.freq
                        recurrence_end = action.recurrence.until
                    
                    result = repo.create_event(
                        title=action.title,
                        date=event_date,
                        time=event_time,
                        end_time=end_time,
                        location=action.location,
                        notes=action.notes,
                        recurrence=recurrence,
                        recurrence_end=recurrence_end,
                    )
                    results.append({"action": "create_event", "success": True, "event": result})
                
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
                    results.append({"action": "update_event", "success": True, "event": result})
                
                elif action.type == "move_event":
                    start_dt = datetime.fromisoformat(action.new_start.replace("Z", "+00:00"))
                    new_date = start_dt.strftime("%Y-%m-%d")
                    new_time = start_dt.strftime("%H:%M")
                    
                    result = repo.move_event(action.event_id, new_date, new_time)
                    results.append({"action": "move_event", "success": True, "event": result})
                
                elif action.type == "delete_event":
                    success = repo.delete_event(action.event_id)
                    results.append({"action": "delete_event", "success": success})
                
            except Exception as e:
                results.append({"action": action.type, "success": False, "error": str(e)})
        
        # Remove the plan after committing
        del _plan_store[plan_id]
        
        return {
            "success": all(r.get("success", False) for r in results),
            "committed_actions": len(results),
            "results": results,
        }
