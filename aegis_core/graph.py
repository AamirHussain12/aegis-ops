import os
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver

from aegis_core.state import State

load_dotenv()

# High precision, low temperature for infrastructure tasks
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1)

def investigator(state: State) -> dict:
    desc = state["incident_description"]
    sys_prompt = "You are a Level 3 Site Reliability Engineer. Analyze the production incident. Identify the likely root cause in exactly two sentences."
    msg = llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=desc)])
    return {"investigation_report": msg.content}

def resolver(state: State) -> dict:
    report = state["investigation_report"]
    sys_prompt = (
        "You are an Infrastructure Auto-Healer. Based on the investigation report, propose a concrete, "
        "single-action bash script or AWS CLI command to fix it (e.g., 'aws ecs update-service ...'). "
        "Do not explain, just provide the command."
    )
    msg = llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=report)])
    return {"proposed_fix": msg.content}

def executor(state: State) -> dict:
    # 🛑 THIS ONLY RUNS AFTER THE GRAPH WAKES BACK UP FROM HUMAN APPROVAL
    if not state.get("is_approved"):
        return {"resolution_log": f"❌ Action aborted by Human Override. Feedback: {state.get('human_feedback', 'None')}"}
    
    fix = state["proposed_fix"]
    sys_prompt = (
        "You are a terminal emulator. A human just approved the following fix. "
        "Write the dummy bash logs simulating a successful execution of this fix. End with 'SYSTEM STABLE'."
    )
    msg = llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=fix)])
    
    return {"resolution_log": msg.content}

def build_aegis_engine() -> CompiledStateGraph:
    builder = StateGraph(State)

    builder.add_node("investigator", investigator)
    builder.add_node("resolver", resolver)
    builder.add_node("executor", executor)

    builder.add_edge(START, "investigator")
    builder.add_edge("investigator", "resolver")
    builder.add_edge("resolver", "executor")
    builder.add_edge("executor", END)

    # --- THE 0.5% MAGIC ---
    # 1. We initialize a Memory Checkpointer (RAM-based for now, can be Postgres later)
    memory = MemorySaver()
    
    # 2. We compile the graph, explicitly telling it to PAUSE right before 'executor'
    return builder.compile(checkpointer=memory, interrupt_before=["executor"])