"""
Variant interpretation history tracking system

This module provides comprehensive tracking of all changes to variant interpretations,
enabling full audit trails for clinical use and regulatory compliance.

Key features:
1. Version control for all interpretations
2. Complete change history with timestamps and users
3. Comparison tools for interpretation evolution
4. Regulatory compliance audit trails
5. Clinical decision support through history analysis
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship, Session
from sqlalchemy.types import Enum as SQLEnum
from enum import Enum

from .base import Base, get_db_session
from .models import VariantInterpretation, TieringResult
from ..models import Evidence, TierResult

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    """Types of changes that can occur to interpretations"""
    INITIAL_CREATION = "initial_creation"
    TIER_CHANGE = "tier_change"
    EVIDENCE_UPDATE = "evidence_update"
    CLINICAL_SIGNIFICANCE_CHANGE = "clinical_significance_change"
    THERAPEUTIC_IMPLICATION_CHANGE = "therapeutic_implication_change"
    TEXT_REVISION = "text_revision"
    REVIEWER_APPROVAL = "reviewer_approval"
    QUALITY_REVIEW = "quality_review"
    GUIDELINE_UPDATE = "guideline_update"
    KB_UPDATE = "kb_update"
    CORRECTION = "correction"


class HistoryStatus(str, Enum):
    """Status of historical interpretation versions"""
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class InterpretationDiff:
    """Represents differences between interpretation versions"""
    field_name: str
    old_value: Any
    new_value: Any
    change_type: str
    impact_level: str  # "low", "medium", "high", "critical"


class InterpretationHistory(Base):
    """Complete history tracking for variant interpretations"""
    __tablename__ = "interpretation_history"
    
    history_id = Column(String(255), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    
    # Link to current interpretation
    interpretation_id = Column(String(255), ForeignKey("variant_interpretations.interpretation_id"))
    variant_id = Column(String(255), ForeignKey("variants.variant_id"))
    case_uid = Column(String(255), ForeignKey("cases.case_uid"))
    
    # Version information
    version_number = Column(Integer, nullable=False)
    parent_history_id = Column(String(255), ForeignKey("interpretation_history.history_id"))
    
    # Change metadata
    change_type = Column(SQLEnum(ChangeType), nullable=False)
    change_summary = Column(Text)
    change_details = Column(JSON)  # Detailed diff information
    change_reason = Column(Text)   # Clinical reasoning for change
    
    # User and timestamp information
    changed_by = Column(String(255), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)
    reviewer_id = Column(String(255))
    reviewed_at = Column(DateTime)
    
    # Snapshot of interpretation at this version
    tier_assignment = Column(JSON)     # Complete TierResult snapshot
    evidence_summary = Column(JSON)    # Evidence list snapshot  
    clinical_significance = Column(String(100))
    therapeutic_implications = Column(Text)
    generated_text = Column(Text)
    confidence_score = Column(String(10))
    
    # Context information
    guideline_version = Column(String(50))  # AMP/VICC guideline version used
    kb_versions = Column(JSON)              # Knowledge base versions
    software_version = Column(String(50))   # Annotation engine version
    
    # Status and quality
    status = Column(SQLEnum(HistoryStatus), default=HistoryStatus.ACTIVE)
    quality_score = Column(Integer)  # 1-5 quality rating
    validation_status = Column(String(50))
    
    # Clinical impact assessment
    clinical_impact_level = Column(String(20))  # "none", "low", "medium", "high", "critical"
    clinical_impact_notes = Column(Text)
    
    # Relationships
    interpretation = relationship("VariantInterpretation", backref="history_versions")
    variant = relationship("Variant", backref="interpretation_history")
    case = relationship("Case", backref="interpretation_history")
    parent_version = relationship("InterpretationHistory", remote_side="InterpretationHistory.history_id")
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_history_interpretation", "interpretation_id"),
        Index("idx_history_variant", "variant_id"),
        Index("idx_history_case", "case_uid"),
        Index("idx_history_version", "interpretation_id", "version_number"),
        Index("idx_history_changed_by_date", "changed_by", "changed_at"),
        Index("idx_history_change_type", "change_type"),
        Index("idx_history_status", "status"),
    )


class InterpretationApprovalWorkflow(Base):
    """Tracks approval workflow for clinical interpretations"""
    __tablename__ = "interpretation_approvals"
    
    approval_id = Column(String(255), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    history_id = Column(String(255), ForeignKey("interpretation_history.history_id"))
    
    # Workflow information
    workflow_stage = Column(String(50))  # "draft", "review", "approved", "rejected"
    approver_id = Column(String(255), nullable=False)
    approval_date = Column(DateTime, default=datetime.utcnow)
    
    # Approval details
    approval_decision = Column(String(20))  # "approve", "reject", "request_changes"
    approval_comments = Column(Text)
    required_changes = Column(JSON)  # List of required changes
    
    # Clinical validation
    clinical_validity = Column(String(20))  # "valid", "invalid", "uncertain"
    evidence_adequacy = Column(String(20))  # "adequate", "inadequate", "marginal"
    therapeutic_relevance = Column(String(20))  # "high", "medium", "low", "none"
    
    # Relationships
    history_entry = relationship("InterpretationHistory", backref="approvals")
    
    # Indexes
    __table_args__ = (
        Index("idx_approval_history", "history_id"),
        Index("idx_approval_stage", "workflow_stage"),
        Index("idx_approval_approver_date", "approver_id", "approval_date"),
    )


class HistoryTracker:
    """Service class for managing interpretation history"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_initial_history(self, 
                             interpretation_id: str,
                             variant_id: str,
                             case_uid: str,
                             tier_result: TierResult,
                             evidence_list: List[Evidence],
                             created_by: str,
                             software_version: str = "1.0") -> str:
        """
        Create initial history entry for a new interpretation
        
        Returns:
            history_id of the created entry
        """
        
        with get_db_session() as session:
            try:
                history_entry = InterpretationHistory(
                    interpretation_id=interpretation_id,
                    variant_id=variant_id,
                    case_uid=case_uid,
                    version_number=1,
                    change_type=ChangeType.INITIAL_CREATION,
                    change_summary="Initial variant interpretation created",
                    change_details={"action": "initial_creation"},
                    changed_by=created_by,
                    tier_assignment=tier_result.model_dump(),
                    evidence_summary=[e.model_dump() for e in evidence_list],
                    clinical_significance=tier_result.tier.value,
                    confidence_score=str(tier_result.confidence),
                    software_version=software_version,
                    status=HistoryStatus.ACTIVE,
                    clinical_impact_level="medium"
                )
                
                session.add(history_entry)
                session.commit()
                
                self.logger.info(f"Created initial history for interpretation {interpretation_id}")
                return history_entry.history_id
                
            except Exception as e:
                session.rollback()
                self.logger.error(f"Error creating initial history: {e}")
                raise
    
    def track_tier_change(self,
                         interpretation_id: str,
                         old_tier_result: TierResult,
                         new_tier_result: TierResult,
                         changed_by: str,
                         change_reason: str) -> str:
        """
        Track a tier assignment change
        
        Returns:
            history_id of the change entry
        """
        
        with get_db_session() as session:
            try:
                # Get current version number
                current_version = self._get_latest_version(session, interpretation_id)
                
                # Calculate diff
                diff_details = self._calculate_tier_diff(old_tier_result, new_tier_result)
                
                # Determine clinical impact
                impact_level = self._assess_clinical_impact(diff_details)
                
                history_entry = InterpretationHistory(
                    interpretation_id=interpretation_id,
                    version_number=current_version + 1,
                    change_type=ChangeType.TIER_CHANGE,
                    change_summary=f"Tier changed from {old_tier_result.tier.value} to {new_tier_result.tier.value}",
                    change_details=diff_details,
                    change_reason=change_reason,
                    changed_by=changed_by,
                    tier_assignment=new_tier_result.model_dump(),
                    clinical_significance=new_tier_result.tier.value,
                    confidence_score=str(new_tier_result.confidence),
                    status=HistoryStatus.ACTIVE,
                    clinical_impact_level=impact_level
                )
                
                # Mark previous version as superseded
                self._supersede_previous_version(session, interpretation_id, current_version)
                
                session.add(history_entry)
                session.commit()
                
                self.logger.info(f"Tracked tier change for interpretation {interpretation_id}")
                return history_entry.history_id
                
            except Exception as e:
                session.rollback()
                self.logger.error(f"Error tracking tier change: {e}")
                raise
    
    def track_evidence_update(self,
                            interpretation_id: str,
                            old_evidence: List[Evidence],
                            new_evidence: List[Evidence],
                            changed_by: str,
                            update_reason: str) -> str:
        """
        Track an evidence update
        
        Returns:
            history_id of the update entry
        """
        
        with get_db_session() as session:
            try:
                current_version = self._get_latest_version(session, interpretation_id)
                
                # Calculate evidence diff
                diff_details = self._calculate_evidence_diff(old_evidence, new_evidence)
                
                history_entry = InterpretationHistory(
                    interpretation_id=interpretation_id,
                    version_number=current_version + 1,
                    change_type=ChangeType.EVIDENCE_UPDATE,
                    change_summary=f"Evidence updated: {len(diff_details['added'])} added, {len(diff_details['removed'])} removed",
                    change_details=diff_details,
                    change_reason=update_reason,
                    changed_by=changed_by,
                    evidence_summary=[e.model_dump() for e in new_evidence],
                    status=HistoryStatus.ACTIVE,
                    clinical_impact_level="medium"
                )
                
                self._supersede_previous_version(session, interpretation_id, current_version)
                
                session.add(history_entry)
                session.commit()
                
                self.logger.info(f"Tracked evidence update for interpretation {interpretation_id}")
                return history_entry.history_id
                
            except Exception as e:
                session.rollback()
                self.logger.error(f"Error tracking evidence update: {e}")
                raise
    
    def get_interpretation_timeline(self, interpretation_id: str) -> List[Dict[str, Any]]:
        """
        Get complete timeline of changes for an interpretation
        
        Returns:
            List of change events in chronological order
        """
        
        with get_db_session() as session:
            try:
                history_entries = session.query(InterpretationHistory).filter(
                    InterpretationHistory.interpretation_id == interpretation_id
                ).order_by(InterpretationHistory.version_number).all()
                
                timeline = []
                for entry in history_entries:
                    timeline.append({
                        "version": entry.version_number,
                        "change_type": entry.change_type.value,
                        "summary": entry.change_summary,
                        "changed_by": entry.changed_by,
                        "changed_at": entry.changed_at.isoformat(),
                        "clinical_impact": entry.clinical_impact_level,
                        "status": entry.status.value,
                        "confidence_score": entry.confidence_score,
                        "change_reason": entry.change_reason
                    })
                
                return timeline
                
            except Exception as e:
                self.logger.error(f"Error getting interpretation timeline: {e}")
                return []
    
    def compare_versions(self, 
                        interpretation_id: str, 
                        version1: int, 
                        version2: int) -> Dict[str, List[InterpretationDiff]]:
        """
        Compare two versions of an interpretation
        
        Returns:
            Dictionary of differences organized by category
        """
        
        with get_db_session() as session:
            try:
                v1_entry = session.query(InterpretationHistory).filter(
                    InterpretationHistory.interpretation_id == interpretation_id,
                    InterpretationHistory.version_number == version1
                ).first()
                
                v2_entry = session.query(InterpretationHistory).filter(
                    InterpretationHistory.interpretation_id == interpretation_id,
                    InterpretationHistory.version_number == version2
                ).first()
                
                if not v1_entry or not v2_entry:
                    return {"error": "One or both versions not found"}
                
                # Compare key fields
                diffs = {
                    "tier_changes": [],
                    "evidence_changes": [],
                    "text_changes": [],
                    "metadata_changes": []
                }
                
                # Compare tier assignments
                if v1_entry.tier_assignment != v2_entry.tier_assignment:
                    diffs["tier_changes"].append(InterpretationDiff(
                        field_name="tier_assignment",
                        old_value=v1_entry.tier_assignment,
                        new_value=v2_entry.tier_assignment,
                        change_type="tier_change",
                        impact_level="high"
                    ))
                
                # Compare evidence
                if v1_entry.evidence_summary != v2_entry.evidence_summary:
                    diffs["evidence_changes"].append(InterpretationDiff(
                        field_name="evidence_summary",
                        old_value=len(v1_entry.evidence_summary or []),
                        new_value=len(v2_entry.evidence_summary or []),
                        change_type="evidence_update",
                        impact_level="medium"
                    ))
                
                # Compare confidence scores
                if v1_entry.confidence_score != v2_entry.confidence_score:
                    diffs["metadata_changes"].append(InterpretationDiff(
                        field_name="confidence_score",
                        old_value=v1_entry.confidence_score,
                        new_value=v2_entry.confidence_score,
                        change_type="confidence_change",
                        impact_level="low"
                    ))
                
                return {k: [d.__dict__ for d in v] for k, v in diffs.items()}
                
            except Exception as e:
                self.logger.error(f"Error comparing versions: {e}")
                return {"error": str(e)}
    
    def get_audit_trail(self, 
                       case_uid: Optional[str] = None,
                       date_range: Optional[Tuple[datetime, datetime]] = None,
                       user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Generate audit trail for regulatory compliance
        
        Returns:
            Comprehensive audit trail with all required information
        """
        
        with get_db_session() as session:
            try:
                query = session.query(InterpretationHistory)
                
                # Apply filters
                if case_uid:
                    query = query.filter(InterpretationHistory.case_uid == case_uid)
                
                if date_range:
                    start_date, end_date = date_range
                    query = query.filter(
                        InterpretationHistory.changed_at >= start_date,
                        InterpretationHistory.changed_at <= end_date
                    )
                
                if user_id:
                    query = query.filter(InterpretationHistory.changed_by == user_id)
                
                entries = query.order_by(InterpretationHistory.changed_at.desc()).all()
                
                audit_trail = []
                for entry in entries:
                    audit_trail.append({
                        "timestamp": entry.changed_at.isoformat(),
                        "user": entry.changed_by,
                        "action": entry.change_type.value,
                        "interpretation_id": entry.interpretation_id,
                        "variant_id": entry.variant_id,
                        "case_uid": entry.case_uid,
                        "summary": entry.change_summary,
                        "clinical_impact": entry.clinical_impact_level,
                        "software_version": entry.software_version,
                        "guideline_version": entry.guideline_version,
                        "validation_status": entry.validation_status
                    })
                
                return audit_trail
                
            except Exception as e:
                self.logger.error(f"Error generating audit trail: {e}")
                return []
    
    def _get_latest_version(self, session: Session, interpretation_id: str) -> int:
        """Get the latest version number for an interpretation"""
        result = session.query(InterpretationHistory.version_number).filter(
            InterpretationHistory.interpretation_id == interpretation_id
        ).order_by(InterpretationHistory.version_number.desc()).first()
        
        return result[0] if result else 0
    
    def _supersede_previous_version(self, session: Session, interpretation_id: str, version: int):
        """Mark previous version as superseded"""
        session.query(InterpretationHistory).filter(
            InterpretationHistory.interpretation_id == interpretation_id,
            InterpretationHistory.version_number == version
        ).update({"status": HistoryStatus.SUPERSEDED})
    
    def _calculate_tier_diff(self, old_tier: TierResult, new_tier: TierResult) -> Dict[str, Any]:
        """Calculate differences between tier results"""
        return {
            "tier_change": {
                "old_tier": old_tier.tier.value,
                "new_tier": new_tier.tier.value,
                "tier_direction": "upgrade" if new_tier.tier.value > old_tier.tier.value else "downgrade"
            },
            "confidence_change": {
                "old_confidence": old_tier.confidence,
                "new_confidence": new_tier.confidence,
                "confidence_delta": new_tier.confidence - old_tier.confidence
            }
        }
    
    def _calculate_evidence_diff(self, old_evidence: List[Evidence], new_evidence: List[Evidence]) -> Dict[str, Any]:
        """Calculate differences between evidence lists"""
        old_codes = {e.code for e in old_evidence}
        new_codes = {e.code for e in new_evidence}
        
        return {
            "added": list(new_codes - old_codes),
            "removed": list(old_codes - new_codes),
            "total_old": len(old_evidence),
            "total_new": len(new_evidence),
            "net_change": len(new_evidence) - len(old_evidence)
        }
    
    def _assess_clinical_impact(self, diff_details: Dict[str, Any]) -> str:
        """Assess clinical impact level of changes"""
        # Simple heuristic - can be enhanced with more sophisticated logic
        if "tier_change" in diff_details:
            tier_change = diff_details["tier_change"]
            if tier_change["tier_direction"] == "upgrade":
                return "high"
            else:
                return "critical"  # Downgrades are serious
        
        return "medium"


# Utility functions for history management
def get_history_tracker() -> HistoryTracker:
    """Get a configured history tracker instance"""
    return HistoryTracker()


def create_approval_workflow(history_id: str, 
                           approver_id: str,
                           workflow_stage: str = "review") -> str:
    """Create an approval workflow entry"""
    
    with get_db_session() as session:
        try:
            approval = InterpretationApprovalWorkflow(
                history_id=history_id,
                workflow_stage=workflow_stage,
                approver_id=approver_id,
                approval_decision="pending"
            )
            
            session.add(approval)
            session.commit()
            
            return approval.approval_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating approval workflow: {e}")
            raise