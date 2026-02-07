"""
Policy Override Store - Dynamic MAS Update System

Allows runtime modification of workflow behavior via policy overrides.
Example: "Don't update addresses, escalate instead and mark as NEEDS_ATTENTION"
"""

from typing import Dict, List, Optional
from datetime import datetime
import json
from pathlib import Path


class PolicyOverride:
    """Represents a single policy override"""
    
    def __init__(
        self,
        override_id: str,
        workflow: str,
        rule_id: str,
        override_action: str,
        original_prompt: str,
        context_updates: Optional[Dict] = None,
        tool_param_overrides: Optional[Dict] = None,
        escalation_reason: Optional[str] = None,
        response_template_override: Optional[str] = None,
        active: bool = True
    ):
        self.override_id = override_id
        self.workflow = workflow
        self.rule_id = rule_id
        self.override_action = override_action
        self.original_prompt = original_prompt
        self.context_updates = context_updates or {}
        self.tool_param_overrides = tool_param_overrides or {}
        self.escalation_reason = escalation_reason
        self.response_template_override = response_template_override
        self.active = active
        self.created_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            "override_id": self.override_id,
            "workflow": self.workflow,
            "rule_id": self.rule_id,
            "override_action": self.override_action,
            "original_prompt": self.original_prompt,
            "context_updates": self.context_updates,
            "tool_param_overrides": self.tool_param_overrides,
            "escalation_reason": self.escalation_reason,
            "response_template_override": self.response_template_override,
            "active": self.active,
            "created_at": self.created_at
        }


class PolicyOverrideStore:
    """
    Stores and manages policy overrides for dynamic workflow modification.
    
    Thread-safe in-memory storage with optional JSON persistence.
    """
    
    def __init__(self, persist_path: Optional[str] = None):
        self.overrides: Dict[str, PolicyOverride] = {}
        self.persist_path = persist_path
        
        if persist_path:
            self._load_from_disk()
    
    def add_override(
        self,
        override_id: str,
        workflow: str,
        rule_id: str,
        override_action: str,
        original_prompt: str,
        **kwargs
    ) -> PolicyOverride:
        """Add a new policy override"""
        override = PolicyOverride(
            override_id=override_id,
            workflow=workflow,
            rule_id=rule_id,
            override_action=override_action,
            original_prompt=original_prompt,
            **kwargs
        )
        
        self.overrides[override_id] = override
        self._persist()
        
        return override
    
    def get_override(self, workflow: str, rule_id: str) -> Optional[PolicyOverride]:
        """
        Get active override for specific workflow + rule.
        Returns None if no active override exists.
        """
        for override in self.overrides.values():
            if (override.workflow == workflow and 
                override.rule_id == rule_id and 
                override.active):
                return override
        
        return None
    
    def get_by_id(self, override_id: str) -> Optional[PolicyOverride]:
        """Get override by ID"""
        return self.overrides.get(override_id)
    
    def list_overrides(self, active_only: bool = False) -> List[PolicyOverride]:
        """List all overrides"""
        overrides = list(self.overrides.values())
        
        if active_only:
            overrides = [o for o in overrides if o.active]
        
        return overrides
    
    def toggle_override(self, override_id: str) -> bool:
        """Toggle override active status. Returns new status."""
        if override_id in self.overrides:
            override = self.overrides[override_id]
            override.active = not override.active
            self._persist()
            return override.active
        
        raise ValueError(f"Override {override_id} not found")
    
    def remove_override(self, override_id: str) -> bool:
        """Remove an override"""
        if override_id in self.overrides:
            del self.overrides[override_id]
            self._persist()
            return True
        
        return False
    
    def clear_all(self):
        """Clear all overrides"""
        self.overrides.clear()
        self._persist()
    
    def _persist(self):
        """Save to disk if persistence is enabled"""
        if not self.persist_path:
            return
        
        path = Path(self.persist_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            override_id: override.to_dict()
            for override_id, override in self.overrides.items()
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _load_from_disk(self):
        """Load from disk if file exists"""
        if not self.persist_path:
            return
        
        path = Path(self.persist_path)
        if not path.exists():
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for override_id, override_data in data.items():
                # Reconstruct PolicyOverride objects
                self.overrides[override_id] = PolicyOverride(**override_data)
        
        except Exception as e:
            print(f"Warning: Failed to load policy overrides: {e}")


# Global instance
_global_store = None


def get_policy_store() -> PolicyOverrideStore:
    """Get the global policy override store"""
    global _global_store
    
    if _global_store is None:
        persist_path = "data/policy_overrides.json"
        _global_store = PolicyOverrideStore(persist_path=persist_path)
    
    return _global_store
