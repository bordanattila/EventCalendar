"""
Tests for agent action plan generation.
"""

import pytest
from datetime import date


class TestActionPlanSchema:
    """Test suite for action plan schemas."""
    
    def test_create_event_action_schema(self):
        """Test CreateEventAction schema validation."""
        from calendar_agent.agent.schemas import CreateEventAction, RecurrenceRule
        
        action = CreateEventAction(
            title="Soccer",
            start="2025-01-07T18:00:00",
            end="2025-01-07T19:00:00",
            recurrence=RecurrenceRule(
                freq="weekly",
                count=8,
                byweekday=["TU"]
            )
        )
        
        assert action.type == "create_event"
        assert action.title == "Soccer"
        assert action.recurrence.freq == "weekly"
        assert action.recurrence.count == 8
    
    def test_move_event_action_schema(self):
        """Test MoveEventAction schema validation."""
        from calendar_agent.agent.schemas import MoveEventAction
        
        action = MoveEventAction(
            event_id=123,
            new_start="2025-01-15T14:00:00",
            reason="Conflict with work meeting"
        )
        
        assert action.type == "move_event"
        assert action.event_id == 123
        assert "Conflict" in action.reason
    
    def test_action_plan_schema(self):
        """Test ActionPlan schema creation."""
        from calendar_agent.agent.schemas import ActionPlan, CreateEventAction
        
        plan = ActionPlan(
            plan_id="plan_test123",
            summary="Adding soccer event",
            actions=[
                CreateEventAction(
                    title="Soccer",
                    start="2025-01-07T18:00:00",
                )
            ],
            warnings=["Time slot is popular"],
            needs_approval=True
        )
        
        assert plan.plan_id == "plan_test123"
        assert len(plan.actions) == 1
        assert plan.needs_approval is True
        assert len(plan.warnings) == 1


class TestChatRequest:
    """Test suite for chat request handling."""
    
    def test_chat_request_basic(self):
        """Test basic chat request."""
        from calendar_agent.agent.schemas import ChatRequest
        
        request = ChatRequest(message="Add soccer every Tuesday at 6pm")
        
        assert request.message == "Add soccer every Tuesday at 6pm"
        assert request.context is None
    
    def test_chat_request_with_context(self):
        """Test chat request with context."""
        from calendar_agent.agent.schemas import ChatRequest
        
        request = ChatRequest(
            message="What's on my calendar?",
            context={
                "timezone": "America/Los_Angeles",
                "user_id": "user123"
            }
        )
        
        assert request.context["timezone"] == "America/Los_Angeles"


class TestEventCRUD:
    """Test event CRUD through API."""
    
    def test_create_event_api(self, test_client):
        """Test creating event through API."""
        response = test_client.post("/events", json={
            "title": "Test Meeting",
            "date": date.today().isoformat(),
            "time": "14:00",
            "recurrence": "none"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Meeting"
        assert "id" in data
    
    def test_list_events_api(self, test_client, sample_events):
        """Test listing events through API."""
        # Create some events first
        for event in sample_events:
            test_client.post("/events", json=event)
        
        response = test_client.get("/events")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= len(sample_events)
    
    def test_search_events_api(self, test_client):
        """Test searching events through API."""
        # Create an event
        test_client.post("/events", json={
            "title": "Special Meeting",
            "date": date.today().isoformat(),
            "time": "10:00",
            "recurrence": "none"
        })
        
        response = test_client.get("/events/search/Special")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any("Special" in e["title"] for e in data)
    
    def test_update_event_api(self, test_client):
        """Test updating event through API."""
        # Create an event
        create_response = test_client.post("/events", json={
            "title": "Original Title",
            "date": date.today().isoformat(),
            "time": "11:00",
            "recurrence": "none"
        })
        event_id = create_response.json()["id"]
        
        # Update it
        response = test_client.put(f"/events/{event_id}", json={
            "title": "Updated Title"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
    
    def test_delete_event_api(self, test_client):
        """Test deleting event through API."""
        # Create an event
        create_response = test_client.post("/events", json={
            "title": "To Delete",
            "date": date.today().isoformat(),
            "time": "12:00",
            "recurrence": "none"
        })
        event_id = create_response.json()["id"]
        
        # Delete it
        response = test_client.delete(f"/events/{event_id}")
        
        assert response.status_code == 200
        
        # Verify it's gone
        get_response = test_client.get(f"/events/{event_id}")
        assert get_response.status_code == 404


class TestHealthCheck:
    """Test health check endpoints."""
    
    def test_health_endpoint(self, test_client):
        """Test basic health check."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint."""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert data["docs"] == "/docs"

