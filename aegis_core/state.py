from typing import TypedDict, Optional

class State(TypedDict, total=False):
    incident_id: str
    incident_description: str
    
    investigation_report: str
    proposed_fix: str
    
    # The 0.5% Magic: HITL (Human-in-the-Loop) variables
    is_approved: Optional[bool]
    human_feedback: Optional[str]
    
    resolution_log: str