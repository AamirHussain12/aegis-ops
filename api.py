from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from aegis_core.graph import build_aegis_engine

app = FastAPI(title="Aegis-Ops API", version="1.0")

# Compile graph with Memory Checkpointer attached
aegis_swarm = build_aegis_engine()

class IncidentRequest(BaseModel):
    thread_id: str
    description: str

class ApprovalRequest(BaseModel):
    thread_id: str
    is_approved: bool
    feedback: str = ""

@app.post("/api/v1/trigger")
async def trigger_incident(payload: IncidentRequest):
    try:
        # Config acts as the memory tracking key for this specific incident thread
        config = {"configurable": {"thread_id": payload.thread_id}}
        initial_state = {"incident_id": payload.thread_id, "incident_description": payload.description}
        
        # Fire the graph! It will run until it hits the interrupt_before rule, then yield/pause.
        for event in aegis_swarm.stream(initial_state, config=config):
            pass 
            
        # Extract the frozen state from LangGraph's memory
        state = aegis_swarm.get_state(config)
        
        return {"status": "waiting_for_approval", "state": state.values}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph Execution Error: {str(e)}")

@app.post("/api/v1/resolve")
async def resolve_incident(payload: ApprovalRequest):
    try:
        # Find the exact memory thread we paused earlier
        config = {"configurable": {"thread_id": payload.thread_id}}
        
        # INJECT the human's decision directly into the frozen graph's state memory
        aegis_swarm.update_state(
            config, 
            {"is_approved": payload.is_approved, "human_feedback": payload.feedback}
        )
        
        # RESUME the graph (passing None continues it from the exact node where it paused)
        for event in aegis_swarm.stream(None, config=config):
            pass
            
        # Get the final state after execution
        state = aegis_swarm.get_state(config)
        
        if payload.is_approved:
            return {"status": "executed", "log": state.values.get("resolution_log")}
        else:
            return {"status": "aborted", "log": state.values.get("resolution_log")}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))