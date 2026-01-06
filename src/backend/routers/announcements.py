"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


def serialize_announcement(announcement: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB document to JSON-serializable dict"""
    if announcement and "_id" in announcement:
        announcement["id"] = str(announcement["_id"])
        del announcement["_id"]
    return announcement


@router.get("")
def get_active_announcements() -> List[Dict[str, Any]]:
    """Get all active announcements (not expired)"""
    current_time = datetime.now().isoformat()
    
    # Find announcements that:
    # - Either have no start date, or start date is in the past
    # - Expiration date is in the future
    announcements = list(announcements_collection.find({
        "$and": [
            {
                "$or": [
                    {"start_date": None},
                    {"start_date": {"$lte": current_time}}
                ]
            },
            {"expiration_date": {"$gte": current_time}}
        ]
    }))
    
    return [serialize_announcement(a) for a in announcements]


@router.get("/all")
def get_all_announcements(username: str) -> List[Dict[str, Any]]:
    """Get all announcements (requires authentication)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    announcements = list(announcements_collection.find({}))
    return [serialize_announcement(a) for a in announcements]


@router.post("")
def create_announcement(
    message: str,
    expiration_date: str,
    username: str,
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new announcement (requires authentication)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Validate dates
    try:
        exp_date = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
        if exp_date <= datetime.now():
            raise HTTPException(status_code=400, detail="Expiration date must be in the future")
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if start_dt >= exp_date:
                raise HTTPException(status_code=400, detail="Start date must be before expiration date")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    announcement = {
        "message": message,
        "start_date": start_date,
        "expiration_date": expiration_date,
        "created_by": username,
        "created_at": datetime.now().isoformat()
    }
    
    result = announcements_collection.insert_one(announcement)
    announcement["id"] = str(result.inserted_id)
    
    return announcement


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: str,
    message: str,
    expiration_date: str,
    username: str,
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """Update an announcement (requires authentication)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Validate dates
    try:
        exp_date = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
        if exp_date <= datetime.now():
            raise HTTPException(status_code=400, detail="Expiration date must be in the future")
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if start_dt >= exp_date:
                raise HTTPException(status_code=400, detail="Start date must be before expiration date")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Convert string ID to ObjectId
    try:
        obj_id = ObjectId(announcement_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    # Update the announcement
    result = announcements_collection.update_one(
        {"_id": obj_id},
        {"$set": {
            "message": message,
            "start_date": start_date,
            "expiration_date": expiration_date,
            "updated_by": username,
            "updated_at": datetime.now().isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    updated = announcements_collection.find_one({"_id": obj_id})
    return serialize_announcement(updated)


@router.delete("/{announcement_id}")
def delete_announcement(announcement_id: str, username: str) -> Dict[str, str]:
    """Delete an announcement (requires authentication)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Convert string ID to ObjectId
    try:
        obj_id = ObjectId(announcement_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    result = announcements_collection.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
