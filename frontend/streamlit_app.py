"""
Streamlit UI for the Task Automation Agent.
"""

import streamlit as st
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path.parent))

from backend.core.orchestrator import TaskOrchestrator
from backend.models import TaskStatus, HumanInputRequest


def main():
    st.set_page_config(
        page_title="Task Automation Agent",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("Intelligent Task Automation Agent")
    st.markdown("""
    An autonomous AI agent that takes high-level goals, breaks them down into tasks, 
    plans execution, adapts to obstacles, and learns from experience.
    """)
    
    # Initialize session state
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = TaskOrchestrator()
    
    if "current_session" not in st.session_state:
        st.session_state.current_session = None
    
    if "pending_requests" not in st.session_state:
        st.session_state.pending_requests = []
    
    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Choose a page",
            ["Execute Goal", "View Progress", "Session History", "Learned Patterns"]
        )
    
    # Main content
    if page == "Execute Goal":
        show_execute_goal()
    elif page == "View Progress":
        show_progress()
    elif page == "Session History":
        show_session_history()
    elif page == "Learned Patterns":
        show_learned_patterns()


def show_execute_goal():
    """Show the goal execution interface."""
    st.header("Execute a Goal")
    
    goal_description = st.text_area(
        "Describe your goal",
        placeholder="e.g., Set up a new Python project with FastAPI, git repository, and README",
        height=100
    )
    
    context = st.text_area(
        "Additional context (optional)",
        placeholder="Any additional information that might help...",
        height=60
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        execute_button = st.button("Execute Goal", type="primary")
    
    if execute_button and goal_description:
        with st.spinner("Executing goal..."):
            try:
                context_dict = {}
                if context:
                    context_dict = {"context": context}
                
                session = st.session_state.orchestrator.execute_goal(
                    goal_description,
                    context_dict
                )
                
                st.session_state.current_session = session
                st.success("Goal execution completed!")
                
                # Show results
                st.subheader("Execution Results")
                show_session_summary(session)
                
            except Exception as e:
                st.error(f"Error executing goal: {str(e)}")
    
    # Show pending human input requests
    if st.session_state.orchestrator.pending_human_inputs:
        st.subheader("Pending Human Input Requests")
        for request_id, request in st.session_state.orchestrator.pending_human_inputs.items():
            with st.expander(f"Request: {request.question[:50]}..."):
                st.write(request.question)
                
                if request.options:
                    response = st.radio(
                        "Choose an option",
                        request.options,
                        key=f"request_{request_id}"
                    )
                else:
                    response = st.text_input(
                        "Your response",
                        key=f"request_{request_id}"
                    )
                
                if st.button("Submit Response", key=f"submit_{request_id}"):
                    result = st.session_state.orchestrator.provide_human_input(
                        request_id,
                        response
                    )
                    if result.get("success"):
                        st.success("Response submitted!")
                        del st.session_state.orchestrator.pending_human_inputs[request_id]
                        st.rerun()
                    else:
                        st.error(f"Error: {result.get('error')}")


def show_progress():
    """Show progress of current execution."""
    st.header("Execution Progress")
    
    if st.session_state.current_session:
        session = st.session_state.current_session
        
        # Overall progress
        progress = st.session_state.orchestrator.progress_tracker.get_progress(
            session.goal,
            session.execution_plan
        )
        
        st.metric("Completion", f"{progress['completion_percentage']:.1f}%")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Completed", progress['completed'])
        with col2:
            st.metric("Failed", progress['failed'])
        with col3:
            st.metric("In Progress", progress['in_progress'])
        with col4:
            st.metric("Pending", progress['pending'])
        
        # Task details
        st.subheader("Task Details")
        task_summary = st.session_state.orchestrator.progress_tracker.get_task_status_summary(
            session.execution_plan
        )
        
        for task_info in task_summary:
            status_emoji = {
                "completed": "✅",
                "failed": "❌",
                "in_progress": "🔄",
                "pending": "⏳"
            }.get(task_info["status"], "❓")
            
            with st.expander(f"{status_emoji} {task_info['description']}"):
                st.write(f"**Status:** {task_info['status']}")
                st.write(f"**Priority:** {task_info['priority']}")
                if task_info.get("error"):
                    st.error(f"Error: {task_info['error']}")
    else:
        st.info("No active session. Execute a goal to see progress.")


def show_session_summary(session):
    """Show a summary of a session."""
    st.write(f"**Goal:** {session.goal.description}")
    st.write(f"**Status:** {session.goal.status.value}")
    
    if session.adaptations:
        st.subheader("Adaptations and Learnings")
        for adaptation in session.adaptations:
            if adaptation.recommendations:
                st.write("**Recommendations:**")
                for rec in adaptation.recommendations:
                    st.write(f"- {rec}")


def show_session_history():
    """Show history of past sessions."""
    st.header("Session History")
    
    orchestrator = st.session_state.orchestrator
    session_ids = orchestrator.memory_manager.list_sessions()
    
    if session_ids:
        selected_id = st.selectbox("Select a session", session_ids)
        
        if selected_id:
            session = orchestrator.memory_manager.load_session(selected_id)
            if session:
                show_session_summary(session)
    else:
        st.info("No past sessions found.")


def show_learned_patterns():
    """Show learned patterns."""
    st.header("Learned Patterns")
    
    orchestrator = st.session_state.orchestrator
    patterns = orchestrator.memory_manager.get_patterns()
    
    if patterns:
        st.write(f"Found {len(patterns)} learned patterns")
        
        pattern_type = st.selectbox(
            "Filter by type",
            ["All"] + list(set(p.pattern_type for p in patterns))
        )
        
        filtered_patterns = patterns
        if pattern_type != "All":
            filtered_patterns = [p for p in patterns if p.pattern_type == pattern_type]
        
        for pattern in filtered_patterns[:20]:  # Show first 20
            with st.expander(f"{pattern.pattern_type} - Confidence: {pattern.confidence:.2f}"):
                st.write(f"**Outcome:** {pattern.outcome}")
                st.write(f"**Context:** {pattern.context}")
                st.write(f"**Usage Count:** {pattern.usage_count}")
    else:
        st.info("No patterns learned yet. Execute some goals to start learning!")


if __name__ == "__main__":
    main()

