"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original participants
    original_participants = {
        "Basketball": ["james@mergington.edu"],
        "Soccer": ["alex@mergington.edu"],
        "Drama Club": ["sarah@mergington.edu", "lucas@mergington.edu"],
        "Art Studio": ["maya@mergington.edu"],
        "Debate Team": ["noah@mergington.edu", "ava@mergington.edu"],
        "Math Olympiad": ["isaac@mergington.edu"],
        "Chess Club": ["michael@mergington.edu", "daniel@mergington.edu"],
        "Programming Class": ["emma@mergington.edu", "sophia@mergington.edu"],
        "Gym Class": ["john@mergington.edu", "olivia@mergington.edu"],
    }
    
    # Apply original state
    from src.app import activities
    for activity_name, participants in original_participants.items():
        activities[activity_name]["participants"] = participants.copy()
    
    yield
    
    # Reset after test
    for activity_name, participants in original_participants.items():
        activities[activity_name]["participants"] = participants.copy()


class TestRoot:
    """Tests for root endpoint"""
    
    def test_root_redirect(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all(self, client, reset_activities):
        """Test that all activities are returned"""
        response = client.get("/activities")
        assert response.status_code == 200
        activities = response.json()
        assert len(activities) == 9
        assert "Basketball" in activities
        assert "Soccer" in activities
        assert "Drama Club" in activities
    
    def test_activities_contain_required_fields(self, client, reset_activities):
        """Test that activities contain all required fields"""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, details in activities.items():
            assert "description" in details
            assert "schedule" in details
            assert "max_participants" in details
            assert "participants" in details
            assert isinstance(details["participants"], list)
    
    def test_basketball_has_initial_participant(self, client, reset_activities):
        """Test that Basketball has the expected initial participant"""
        response = client.get("/activities")
        activities = response.json()
        assert "james@mergington.edu" in activities["Basketball"]["participants"]


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_new_participant(self, client, reset_activities):
        """Test successful signup for a new participant"""
        response = client.post(
            "/activities/Basketball/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "newstudent@mergington.edu" in data["message"]
        assert "Basketball" in data["message"]
    
    def test_signup_adds_to_participants(self, client, reset_activities):
        """Test that signup actually adds the participant to the list"""
        client.post("/activities/Basketball/signup?email=newstudent@mergington.edu")
        
        response = client.get("/activities")
        activities = response.json()
        assert "newstudent@mergington.edu" in activities["Basketball"]["participants"]
    
    def test_signup_duplicate_fails(self, client, reset_activities):
        """Test that duplicate signup fails"""
        response = client.post(
            "/activities/Basketball/signup?email=james@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signup to non-existent activity fails"""
        response = client.post(
            "/activities/NonexistentActivity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_multiple_different_activities(self, client, reset_activities):
        """Test that same student can signup for multiple activities"""
        email = "multiactivity@mergington.edu"
        
        response1 = client.post(f"/activities/Basketball/signup?email={email}")
        assert response1.status_code == 200
        
        response2 = client.post(f"/activities/Soccer/signup?email={email}")
        assert response2.status_code == 200
        
        # Verify both signups
        response = client.get("/activities")
        activities = response.json()
        assert email in activities["Basketball"]["participants"]
        assert email in activities["Soccer"]["participants"]


class TestUnregister:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_existing_participant(self, client, reset_activities):
        """Test successful unregister of a participant"""
        response = client.delete(
            "/activities/Basketball/unregister?email=james@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "james@mergington.edu" in data["message"]
        assert "Unregistered" in data["message"]
    
    def test_unregister_removes_from_participants(self, client, reset_activities):
        """Test that unregister actually removes the participant"""
        client.delete("/activities/Basketball/unregister?email=james@mergington.edu")
        
        response = client.get("/activities")
        activities = response.json()
        assert "james@mergington.edu" not in activities["Basketball"]["participants"]
    
    def test_unregister_nonexistent_participant_fails(self, client, reset_activities):
        """Test that unregistering non-existent participant fails"""
        response = client.delete(
            "/activities/Basketball/unregister?email=nonexistent@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"]
    
    def test_unregister_nonexistent_activity_fails(self, client):
        """Test that unregister from non-existent activity fails"""
        response = client.delete(
            "/activities/NonexistentActivity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_then_unregister(self, client, reset_activities):
        """Test signup followed by unregister"""
        email = "temp@mergington.edu"
        
        # Signup
        response1 = client.post(f"/activities/Soccer/signup?email={email}")
        assert response1.status_code == 200
        
        # Verify signup
        response = client.get("/activities")
        assert email in response.json()["Soccer"]["participants"]
        
        # Unregister
        response2 = client.delete(f"/activities/Soccer/unregister?email={email}")
        assert response2.status_code == 200
        
        # Verify unregister
        response = client.get("/activities")
        assert email not in response.json()["Soccer"]["participants"]


class TestIntegration:
    """Integration tests for multiple operations"""
    
    def test_multiple_signups_and_unregisters(self, client, reset_activities):
        """Test multiple signups and unregisters in sequence"""
        email1 = "student1@mergington.edu"
        email2 = "student2@mergington.edu"
        
        # Both signup for Basketball
        client.post(f"/activities/Basketball/signup?email={email1}")
        client.post(f"/activities/Basketball/signup?email={email2}")
        
        response = client.get("/activities")
        assert email1 in response.json()["Basketball"]["participants"]
        assert email2 in response.json()["Basketball"]["participants"]
        
        # Unregister first student
        client.delete(f"/activities/Basketball/unregister?email={email1}")
        
        response = client.get("/activities")
        assert email1 not in response.json()["Basketball"]["participants"]
        assert email2 in response.json()["Basketball"]["participants"]
    
    def test_availability_after_signup_and_unregister(self, client, reset_activities):
        """Test that availability updates correctly after signup and unregister"""
        response1 = client.get("/activities")
        initial_basket = response1.json()["Basketball"]
        initial_spots = initial_basket["max_participants"] - len(initial_basket["participants"])
        
        # Signup
        email = "availability@mergington.edu"
        client.post(f"/activities/Basketball/signup?email={email}")
        
        response2 = client.get("/activities")
        after_signup_spots = (
            response2.json()["Basketball"]["max_participants"] 
            - len(response2.json()["Basketball"]["participants"])
        )
        assert after_signup_spots == initial_spots - 1
        
        # Unregister
        client.delete(f"/activities/Basketball/unregister?email={email}")
        
        response3 = client.get("/activities")
        after_unregister_spots = (
            response3.json()["Basketball"]["max_participants"]
            - len(response3.json()["Basketball"]["participants"])
        )
        assert after_unregister_spots == initial_spots
