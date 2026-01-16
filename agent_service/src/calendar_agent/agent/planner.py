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
    
    def _parse_agent_response(self, messages: List, tool_calls: List, user_message: str = "") -> ActionPlan:
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
        
        # Determine intent from USER'S original message first (most reliable)
        user_lower = user_message.lower() if user_message else ""
        response_lower = response.lower()
        
        # Detect intent - check user message first, then response
        # Priority: delete > move > create (to avoid false positives)
        
        intent = None
        
        # Check for delete/remove intent (highest priority for destructive actions)
        delete_keywords = ["delete", "cancel", "remove", "drop", "clear"]
        if any(word in user_lower for word in delete_keywords):
            intent = "delete"
        elif any(word in response_lower for word in delete_keywords):
            # Also check response doesn't just mention "remove" in passing
            if re.search(r'\b(remove|delete|cancel)\b.*\bevent\b', response_lower) or \
               re.search(r'\bevent\b.*\b(remove|delete|cancel)\b', response_lower):
                intent = "delete"
        
        # Check for move/reschedule intent
        if not intent:
            move_keywords = ["move", "reschedule", "postpone", "change the time", "change the date"]
            if any(word in user_lower for word in move_keywords):
                intent = "move"
            elif any(word in response_lower for word in move_keywords):
                intent = "move"
        
        # Check for create intent (only if no delete/move detected)
        if not intent:
            # Use word boundaries to avoid "schedule" in "from the schedule"
            create_patterns = [
                r'\b(add|create|schedule|book|set up)\s+(a|an|the)?\s*\w+',  # "add a meeting"
                r'\bnew event\b',
            ]
            for pattern in create_patterns:
                if re.search(pattern, user_lower):
                    intent = "create"
                    break
            
            # If still no intent and response suggests creating
            if not intent and any(word in response_lower for word in ["i will create", "i'll add", "creating", "adding"]):
                intent = "create"
        
        # Execute based on detected intent
        if intent == "delete":
            action = self._extract_delete_action(response, tool_calls)
            if action:
                actions.append(action)
        elif intent == "move":
            action = self._extract_move_action(response, tool_calls)
            if action:
                actions.append(action)
        elif intent == "create":
            action = self._extract_create_action(response, tool_calls, user_message)
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
    
    def _extract_create_action(self, response: str, tool_calls: List, user_message: str = "") -> Optional[CreateEventAction]:
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
        
        # If no date from tools, extract from user message
        if not parsed_date and user_message:
            parsed_date = self._extract_date_from_text(user_message)
        
        # Last resort: today's date
        if not parsed_date:
            parsed_date = date.today().isoformat()
        
        # Extract title from response - look for JSON action blocks first
        title = None
        location = None
        notes = None
        recurrence = None
        
        # Try to find JSON action block in response
        json_match = re.search(r'\{[^{}]*"type"\s*:\s*"create_event"[^{}]*\}', response, re.DOTALL)
        if json_match:
            try:
                action_json = json.loads(json_match.group())
                title = action_json.get("title")
                if action_json.get("start"):
                    # Parse datetime from start field
                    start_str = action_json.get("start")
                    if "T" in start_str:
                        date_part, time_part = start_str.split("T")
                        parsed_date = date_part
                        parsed_time = time_part[:5]  # HH:MM
                location = action_json.get("location")
                notes = action_json.get("notes")
                recurrence = action_json.get("recurrence")
            except json.JSONDecodeError:
                pass
        
        # If no JSON found, try to extract title from quoted text
        if not title:
            quotes = re.findall(r'"([^"]+)"', response)
            if quotes:
                # Filter out JSON-like values
                for q in quotes:
                    if q not in ["create_event", "update_event", "move_event", "delete_event"]:
                        title = q
                        break
        
        # Still no title? Try to extract from common patterns in response
        if not title:
            # Look for "title": "Something" pattern
            title_match = re.search(r'"title"\s*:\s*"([^"]+)"', response)
            if title_match:
                title = title_match.group(1)
        
        # Still no title? Extract from user's original message
        if not title and user_message:
            title = self._extract_title_from_user_message(user_message)
        
        # Extract time from user message first, then response
        if not parsed_time and user_message:
            parsed_time = self._extract_time_from_text(user_message)
        
        # Extract time from response if not found in user message
        if not parsed_time:
            parsed_time = self._extract_time_from_text(response)
        
        # Default title if nothing found
        if not title:
            title = "New Event"
        
        # Build start datetime
        if parsed_time:
            start = f"{parsed_date}T{parsed_time}:00"
        else:
            # All-day event
            start = f"{parsed_date}T00:00:00"
        
        return CreateEventAction(
            title=title,
            start=start,
            end=None,
            location=location,
            notes=notes,
            recurrence=recurrence,
        )
    
    def _extract_title_from_user_message(self, message: str) -> Optional[str]:
        """Extract event title from user's natural language message."""
        message_lower = message.lower()
        
        # Common patterns: "add/schedule/create [a] <title> [for/on/at]..."
        patterns = [
            # "schedule a car appointment for tomorrow"
            r'(?:add|schedule|create|book|set up)\s+(?:a|an)?\s*(.+?)\s+(?:for|on|at|tomorrow|today|next|this)',
            # "car appointment tomorrow at 10"
            r'^(.+?)\s+(?:tomorrow|today|on|for|at\s+\d)',
            # "schedule dinner tonight"
            r'(?:add|schedule|create|book)\s+(.+?)\s+(?:tonight|this evening)',
            # "add meeting at 3pm"
            r'(?:add|schedule|create|book)\s+(?:a|an)?\s*(.+?)\s+at\s+\d',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                title = match.group(1).strip()
                # Clean up common words
                title = re.sub(r'^(a|an|the)\s+', '', title)
                # Remove trailing prepositions
                title = re.sub(r'\s+(for|on|at|to)$', '', title)
                if title and len(title) > 1:
                    # Capitalize first letter of each word
                    return title.title()
        
        return None
    
    def _extract_time_from_text(self, text: str) -> Optional[str]:
        """Extract time from text, converting to 24-hour format."""
        # Look for 24-hour time patterns like 18:00, 10:00
        time_match = re.search(r'\b(\d{1,2}):(\d{2})\b', text)
        if time_match:
            hour = int(time_match.group(1))
            minute = time_match.group(2)
            if 0 <= hour <= 23:
                return f"{hour:02d}:{minute}"
        
        # Look for "at X pm/am" patterns
        time_12h = re.search(r'\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)\b', text, re.IGNORECASE)
        if time_12h:
            hour = int(time_12h.group(1))
            minute = time_12h.group(2) or "00"
            ampm = time_12h.group(3).lower().replace('.', '')
            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            return f"{hour:02d}:{minute}"
        
        # Look for standalone time with am/pm (e.g., "10am", "6pm")
        time_compact = re.search(r'\b(\d{1,2})(am|pm)\b', text, re.IGNORECASE)
        if time_compact:
            hour = int(time_compact.group(1))
            ampm = time_compact.group(2).lower()
            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            return f"{hour:02d}:00"
        
        # Look for "at X" where X is a number between 0-23 (24-hour time without minutes)
        time_24h_simple = re.search(r'\bat\s+(\d{1,2})(?:\s|$|[,.])', text)
        if time_24h_simple:
            hour = int(time_24h_simple.group(1))
            if 0 <= hour <= 23:
                return f"{hour:02d}:00"
        
        return None
    
    def _extract_date_from_text(self, text: str) -> Optional[str]:
        """Extract date from text, handling relative dates like 'tomorrow', 'today', day names."""
        from datetime import timedelta
        
        text_lower = text.lower()
        today = date.today()
        
        # Handle "today"
        if "today" in text_lower or "tonight" in text_lower or "this evening" in text_lower:
            return today.isoformat()
        
        # Handle "tomorrow"
        if "tomorrow" in text_lower:
            return (today + timedelta(days=1)).isoformat()
        
        # Handle "day after tomorrow"
        if "day after tomorrow" in text_lower:
            return (today + timedelta(days=2)).isoformat()
        
        # Handle day names (next Monday, this Tuesday, etc.)
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for i, day_name in enumerate(day_names):
            if day_name in text_lower:
                # Calculate days until that day
                current_weekday = today.weekday()  # Monday = 0
                target_weekday = i
                days_ahead = target_weekday - current_weekday
                if days_ahead <= 0:  # Target day is today or in the past, go to next week
                    days_ahead += 7
                return (today + timedelta(days=days_ahead)).isoformat()
        
        # Handle explicit date formats (January 17, 17th January, 2026-01-17)
        # ISO format
        iso_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
        if iso_match:
            return iso_match.group(1)
        
        # Month day format (January 17, Jan 17th)
        months = {
            "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
            "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6,
            "july": 7, "jul": 7, "august": 8, "aug": 8, "september": 9, "sep": 9,
            "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12
        }
        for month_name, month_num in months.items():
            # "January 17" or "January 17th"
            pattern = rf'\b{month_name}\s+(\d{{1,2}})(?:st|nd|rd|th)?\b'
            match = re.search(pattern, text_lower)
            if match:
                day = int(match.group(1))
                year = today.year
                # If the date has passed this year, assume next year
                try:
                    target_date = date(year, month_num, day)
                    if target_date < today:
                        target_date = date(year + 1, month_num, day)
                    return target_date.isoformat()
                except ValueError:
                    pass
            
            # "17 January" or "17th January"
            pattern = rf'\b(\d{{1,2}})(?:st|nd|rd|th)?\s+{month_name}\b'
            match = re.search(pattern, text_lower)
            if match:
                day = int(match.group(1))
                year = today.year
                try:
                    target_date = date(year, month_num, day)
                    if target_date < today:
                        target_date = date(year + 1, month_num, day)
                    return target_date.isoformat()
                except ValueError:
                    pass
        
        return None
    
    def _extract_move_action(self, response: str, tool_calls: List) -> Optional[MoveEventAction]:
        """Extract move event action from agent response."""
        event_id = None
        event_title = None
        new_date = None
        new_time = None
        
        for call in tool_calls:
            result = call.get("result", {})
            
            # Handle string results (JSON)
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    continue
            
            if not isinstance(result, dict):
                continue
            
            if call.get("name") in ["search_events_tool", "list_events_tool"]:
                events = result.get("events", [])
                if events and isinstance(events, list) and len(events) > 0:
                    event_id = events[0].get("id")
                    event_title = events[0].get("title")
            elif call.get("name") == "parse_datetime_tool":
                new_date = result.get("date")
                new_time = result.get("time")
            elif call.get("name") == "get_next_weekday_tool":
                new_date = result.get("date")
        
        # Extract time from response if not found in tool calls
        if not new_time:
            time_match = re.search(r'\b(\d{1,2}:\d{2})\b', response)
            if time_match:
                new_time = time_match.group(1).zfill(5)
        
        # If no event_id from tools, try to find event by title from response
        if not event_id:
            title_match = re.search(r'"([^"]+)"', response)
            if title_match:
                event_title = title_match.group(1)
                try:
                    events = self.repo.search_events(event_title)
                    if events:
                        event_id = events[0].id
                except Exception:
                    pass
        
        if event_id and new_date:
            if new_time:
                new_start = f"{new_date}T{new_time}:00"
            else:
                new_start = f"{new_date}T00:00:00"  # All-day
            return MoveEventAction(
                event_id=event_id,
                new_start=new_start,
            )
        
        return None
    
    def _extract_delete_action(self, response: str, tool_calls: List) -> Optional[DeleteEventAction]:
        """Extract delete event action from agent response."""
        event_id = None
        event_title = None
        
        # Try to find event from tool calls
        for call in tool_calls:
            result = call.get("result", {})
            
            # Handle string results (JSON)
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    continue
            
            if not isinstance(result, dict):
                continue
                
            # Check search_events_tool and list_events_tool
            if call.get("name") in ["search_events_tool", "list_events_tool"]:
                events = result.get("events", [])
                if events and isinstance(events, list) and len(events) > 0:
                    event_id = events[0].get("id")
                    event_title = events[0].get("title")
                    break
        
        # If no event_id from tools, try to find event by title from response
        if not event_id:
            # Extract title from response
            title_match = re.search(r'"([^"]+)".*(?:scheduled|event|remove|delete)', response, re.IGNORECASE)
            if not title_match:
                title_match = re.search(r'(?:event|remove|delete).*"([^"]+)"', response, re.IGNORECASE)
            
            if title_match:
                event_title = title_match.group(1)
                # Search database for this event
                try:
                    events = self.repo.search_events(event_title)
                    if events:
                        event_id = events[0].id
                except Exception:
                    pass
        
        # Still no event_id? Try extracting from response patterns like "event_id: 123"
        if not event_id:
            id_match = re.search(r'(?:event_id|id)[:\s]+(\d+)', response, re.IGNORECASE)
            if id_match:
                event_id = int(id_match.group(1))
        
        if event_id:
            return DeleteEventAction(
                event_id=event_id,
                reason=f"User requested deletion of '{event_title}'" if event_title else "User requested deletion",
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
            plan = self._parse_agent_response(messages, tool_calls, request.message)
            
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
