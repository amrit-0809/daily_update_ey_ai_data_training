from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_tasks():
    response = client.get("/tasks")

    assert response.status_code == 200
    # assert response.json() == []

def test_get_tasks_returns_list():
    response = client.get("/tasks")

    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_task_by_id():
    response = client.get("/tasks/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1

def test_get_non_existing_task():
    response = client.get("/tasks/999")

    assert response.status_code == 404

def test_add_task():
    response = client.post(
        "/tasks",
        json={
            "id": 4,
            "title": "Check server logs",
            "status": "Pending"
        }
    )

    assert response.status_code == 200
    assert response.json()["id"] == 4
    assert response.json()["title"] == "Check server logs"


def test_add_invalid_task():
    response = client.post(
        "/tasks",
        json={
            "id": 5,
            "title": "Invalid Task"
        }
    )

    assert response.status_code == 422

def test_update_task():
    response = client.put(
        "/tasks/2",
        json={
            "id": 2,
            "title": "Review invoice",
            "status": "Completed"
        }
    )

    assert response.status_code == 200
    assert response.json()["task"]["status"] == "Completed"


def test_delete_task():
    response = client.delete("/tasks/3")

    assert response.status_code == 200
    assert response.json()["message"] == "Task deleted successfully"

def test_get_deleted_task():
    response = client.get("/tasks/3")

    assert response.status_code == 404
