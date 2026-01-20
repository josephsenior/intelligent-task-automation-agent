"""
Memory Manager - Manages storage and retrieval of learned patterns and session data.
Implements Memory pattern.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models import Goal, GoalSession, LearnedPattern


class MemoryManager:
    """Manages memory storage and retrieval."""

    def __init__(
        self, memory_dir: str = "data/memory", sessions_dir: str = "data/sessions"
    ):
        """
        Initialize the memory manager.

        Args:
            memory_dir: Directory for storing learned patterns
            sessions_dir: Directory for storing goal sessions
        """
        self.memory_dir = Path(memory_dir)
        self.sessions_dir = Path(sessions_dir)

        # Create directories if they don't exist
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        self.patterns_file = self.memory_dir / "learned_patterns.json"
        self._patterns: List[LearnedPattern] = []
        self._load_patterns()

    def save_pattern(self, pattern: LearnedPattern):
        """
        Save a learned pattern to memory.

        Args:
            pattern: Pattern to save
        """
        self._patterns.append(pattern)
        self._save_patterns()

    def save_patterns(self, patterns: List[LearnedPattern]):
        """
        Save multiple learned patterns.

        Args:
            patterns: List of patterns to save
        """
        self._patterns.extend(patterns)
        self._save_patterns()

    def get_patterns(
        self,
        pattern_type: Optional[str] = None,
        context_filter: Optional[Dict[str, Any]] = None,
    ) -> List[LearnedPattern]:
        """
        Retrieve learned patterns.

        Args:
            pattern_type: Filter by pattern type
            context_filter: Filter by context keys

        Returns:
            List of matching patterns
        """
        patterns = self._patterns

        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]

        if context_filter:
            filtered = []
            for pattern in patterns:
                match = True
                for key, value in context_filter.items():
                    if key not in pattern.context or pattern.context[key] != value:
                        match = False
                        break
                if match:
                    filtered.append(pattern)
            patterns = filtered

        # Sort by confidence and usage count
        patterns.sort(key=lambda p: (p.confidence, p.usage_count), reverse=True)

        return patterns

    def update_pattern_usage(self, pattern_id: str):
        """
        Update pattern usage statistics.

        Args:
            pattern_id: ID of the pattern to update
        """
        for pattern in self._patterns:
            if pattern.id == pattern_id:
                pattern.usage_count += 1
                pattern.last_used = datetime.now()
                self._save_patterns()
                break

    def save_session(self, session: GoalSession):
        """
        Save a goal session.

        Args:
            session: Session to save
        """
        session_file = self.sessions_dir / f"{session.id}.json"

        session_data = {
            "id": session.id,
            "goal": session.goal.dict(),
            "execution_plan": session.execution_plan.dict(),
            "results": [r.dict() for r in session.results],
            "adaptations": [a.dict() for a in session.adaptations],
            "human_inputs": [h.dict() for h in session.human_inputs],
            "reasoning_results": [r.dict() for r in session.reasoning_results],
            "started_at": session.started_at.isoformat(),
            "completed_at": session.completed_at.isoformat()
            if session.completed_at
            else None,
        }

        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, default=str)

    def load_session(self, session_id: str) -> Optional[GoalSession]:
        """
        Load a goal session.

        Args:
            session_id: ID of the session to load

        Returns:
            GoalSession or None if not found
        """
        session_file = self.sessions_dir / f"{session_id}.json"

        if not session_file.exists():
            return None

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            # Reconstruct session from data
            # This is simplified - in production you'd want proper deserialization
            from ..models import ExecutionPlan, GoalSession

            goal = Goal(**session_data["goal"])
            execution_plan = ExecutionPlan(**session_data["execution_plan"])

            session = GoalSession(
                id=session_data["id"],
                goal=goal,
                execution_plan=execution_plan,
                started_at=datetime.fromisoformat(session_data["started_at"]),
                completed_at=datetime.fromisoformat(session_data["completed_at"])
                if session_data.get("completed_at")
                else None,
            )

            return session

        except Exception as e:
            print(f"Error loading session: {e}")
            return None

    def list_sessions(self) -> List[str]:
        """List all session IDs."""
        session_files = list(self.sessions_dir.glob("*.json"))
        return [f.stem for f in session_files]

    def _load_patterns(self):
        """Load learned patterns from disk."""
        if not self.patterns_file.exists():
            return

        try:
            with open(self.patterns_file, "r", encoding="utf-8") as f:
                patterns_data = json.load(f)

            self._patterns = [LearnedPattern(**p) for p in patterns_data]

        except Exception as e:
            print(f"Error loading patterns: {e}")
            self._patterns = []

    def _save_patterns(self):
        """Save learned patterns to disk."""
        try:
            patterns_data = [p.dict() for p in self._patterns]

            with open(self.patterns_file, "w", encoding="utf-8") as f:
                json.dump(patterns_data, f, indent=2, default=str)

        except Exception as e:
            print(f"Error saving patterns: {e}")
