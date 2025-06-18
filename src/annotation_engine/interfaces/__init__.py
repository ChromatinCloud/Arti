"""
Shared interfaces for component communication

These interfaces define contracts between major components to enable
parallel development without conflicts.
"""

from .validation_interfaces import (
    ValidatedInput,
    ValidationResult,
    ValidationError,
    InputValidatorProtocol
)

from .workflow_interfaces import (
    WorkflowContext,
    WorkflowRoute,
    WorkflowRouterProtocol,
    AnalysisType
)

__all__ = [
    # Validation interfaces
    'ValidatedInput',
    'ValidationResult', 
    'ValidationError',
    'InputValidatorProtocol',
    
    # Workflow interfaces
    'WorkflowContext',
    'WorkflowRoute',
    'WorkflowRouterProtocol',
    'AnalysisType'
]