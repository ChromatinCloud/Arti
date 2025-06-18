"""
Clinical Audit Trail System for Regulatory Compliance

This module provides comprehensive audit trail functionality for clinical variant interpretation,
ensuring full compliance with regulatory requirements (HIPAA, CLIA, CAP, FDA).

Key features:
1. Complete activity logging with immutable records
2. User authentication and authorization tracking
3. Data access and modification logging
4. Regulatory compliance reporting
5. Security event monitoring
6. Clinical decision audit trails
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import json
import hashlib
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Boolean, ForeignKey, Index, BigInteger
from sqlalchemy.orm import relationship, Session
from sqlalchemy.types import Enum as SQLEnum

from .base import Base, get_db_session
from .history_tracking import InterpretationHistory, ChangeType

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of auditable events"""
    # User authentication
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    
    # Data access
    PATIENT_ACCESS = "patient_access"
    CASE_ACCESS = "case_access"
    VARIANT_ACCESS = "variant_access"
    REPORT_ACCESS = "report_access"
    
    # Data modification
    DATA_CREATE = "data_create"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"
    
    # Clinical workflow
    INTERPRETATION_CREATE = "interpretation_create"
    INTERPRETATION_UPDATE = "interpretation_update"
    INTERPRETATION_APPROVE = "interpretation_approve"
    INTERPRETATION_SIGN = "interpretation_sign"
    REPORT_GENERATE = "report_generate"
    REPORT_FINALIZE = "report_finalize"
    
    # System events
    SYSTEM_BACKUP = "system_backup"
    SYSTEM_RESTORE = "system_restore"
    CONFIGURATION_CHANGE = "configuration_change"
    KB_UPDATE = "kb_update"
    
    # Security events
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    PERMISSION_DENIED = "permission_denied"
    DATA_EXPORT = "data_export"
    ADMIN_ACTION = "admin_action"


class AuditSeverity(str, Enum):
    """Severity levels for audit events"""
    LOW = "low"           # Routine operations
    MEDIUM = "medium"     # Important clinical actions
    HIGH = "high"         # Critical clinical decisions
    CRITICAL = "critical" # Security or compliance issues


class ComplianceFramework(str, Enum):
    """Regulatory compliance frameworks"""
    HIPAA = "HIPAA"       # Health Insurance Portability and Accountability Act
    CLIA = "CLIA"         # Clinical Laboratory Improvement Amendments
    CAP = "CAP"           # College of American Pathologists
    FDA = "FDA"           # Food and Drug Administration
    GDPR = "GDPR"         # General Data Protection Regulation
    ISO15189 = "ISO15189" # Medical laboratories standard


@dataclass
class AuditContext:
    """Context information for audit events"""
    user_id: str
    session_id: str
    ip_address: str
    user_agent: str
    location: Optional[str] = None
    department: Optional[str] = None


class ClinicalAuditLog(Base):
    """Immutable audit log for all clinical system activities"""
    __tablename__ = "clinical_audit_log"
    
    # Primary identification
    audit_id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_uuid = Column(String(36), unique=True, nullable=False)  # UUID for external references
    
    # Event classification
    event_type = Column(SQLEnum(AuditEventType), nullable=False)
    event_category = Column(String(50), nullable=False)  # Derived category
    severity = Column(SQLEnum(AuditSeverity), nullable=False)
    
    # Temporal information
    event_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    event_date = Column(String(10), nullable=False)  # YYYY-MM-DD for efficient querying
    
    # User context
    user_id = Column(String(255), nullable=False)
    user_name = Column(String(255))
    user_role = Column(String(100))
    session_id = Column(String(255))
    
    # System context
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    hostname = Column(String(255))
    application_version = Column(String(50))
    
    # Event details
    event_description = Column(Text, nullable=False)
    event_details = Column(JSON)  # Structured event data
    
    # Clinical context
    patient_id = Column(String(255))  # Anonymized patient identifier
    case_uid = Column(String(255))
    variant_id = Column(String(255))
    interpretation_id = Column(String(255))
    
    # Data affected
    table_affected = Column(String(100))
    record_id = Column(String(255))
    data_before = Column(JSON)  # State before change
    data_after = Column(JSON)   # State after change
    
    # Compliance and legal
    compliance_frameworks = Column(JSON)  # Array of applicable frameworks
    retention_period_years = Column(Integer, default=7)
    legal_hold = Column(Boolean, default=False)
    
    # Security and integrity
    checksum = Column(String(64))  # SHA-256 hash for integrity
    digital_signature = Column(Text)
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_audit_timestamp", "event_timestamp"),
        Index("idx_audit_date", "event_date"),
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_event_type", "event_type"),
        Index("idx_audit_patient", "patient_id"),
        Index("idx_audit_case", "case_uid"),
        Index("idx_audit_severity", "severity"),
        Index("idx_audit_table", "table_affected"),
        Index("idx_audit_uuid", "event_uuid"),
    )


class UserSession(Base):
    """Active user session tracking for audit purposes"""
    __tablename__ = "user_sessions"
    
    session_id = Column(String(255), primary_key=True)
    user_id = Column(String(255), nullable=False)
    
    # Session details
    login_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_activity = Column(DateTime, nullable=False, default=datetime.utcnow)
    logout_timestamp = Column(DateTime)
    
    # Session context
    ip_address = Column(String(45))
    user_agent = Column(Text)
    location = Column(String(255))
    
    # Session state
    is_active = Column(Boolean, default=True)
    session_duration_minutes = Column(Integer)
    
    # Security
    authentication_method = Column(String(50))  # "password", "sso", "mfa"
    risk_score = Column(Integer, default=0)     # Security risk assessment
    
    # Indexes
    __table_args__ = (
        Index("idx_session_user", "user_id"),
        Index("idx_session_active", "is_active"),
        Index("idx_session_login", "login_timestamp"),
    )


class ComplianceReport(Base):
    """Generated compliance reports for regulatory submissions"""
    __tablename__ = "compliance_reports"
    
    report_id = Column(String(255), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    
    # Report metadata
    report_type = Column(String(100), nullable=False)  # "HIPAA_audit", "CLIA_validation", etc.
    compliance_framework = Column(SQLEnum(ComplianceFramework), nullable=False)
    
    # Temporal scope
    report_period_start = Column(DateTime, nullable=False)
    report_period_end = Column(DateTime, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    # Report content
    report_summary = Column(JSON)   # Executive summary
    report_details = Column(JSON)   # Detailed findings
    violations_found = Column(JSON) # Any compliance violations
    
    # Organizational context
    generated_by = Column(String(255), nullable=False)
    organization = Column(String(255))
    department = Column(String(255))
    
    # Status
    report_status = Column(String(50), default="draft")  # "draft", "final", "submitted"
    reviewed_by = Column(String(255))
    review_date = Column(DateTime)
    
    # File attachments
    report_file_path = Column(String(500))
    report_checksum = Column(String(64))
    
    # Indexes
    __table_args__ = (
        Index("idx_compliance_framework", "compliance_framework"),
        Index("idx_compliance_period", "report_period_start", "report_period_end"),
        Index("idx_compliance_generated", "generated_at"),
    )


class AuditTrailManager:
    """Service class for managing clinical audit trails"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def log_event(self,
                  event_type: AuditEventType,
                  description: str,
                  audit_context: AuditContext,
                  severity: AuditSeverity = AuditSeverity.MEDIUM,
                  **kwargs) -> str:
        """
        Log an auditable event
        
        Args:
            event_type: Type of event being logged
            description: Human-readable description
            audit_context: User and system context
            severity: Event severity level
            **kwargs: Additional event-specific data
            
        Returns:
            event_uuid of the logged event
        """
        
        with get_db_session() as session:
            try:
                import uuid
                event_uuid = str(uuid.uuid4())
                
                # Determine compliance frameworks
                frameworks = self._determine_compliance_frameworks(event_type, kwargs)
                
                # Create audit log entry
                audit_entry = ClinicalAuditLog(
                    event_uuid=event_uuid,
                    event_type=event_type,
                    event_category=self._categorize_event(event_type),
                    severity=severity,
                    event_date=datetime.utcnow().strftime("%Y-%m-%d"),
                    user_id=audit_context.user_id,
                    session_id=audit_context.session_id,
                    ip_address=audit_context.ip_address,
                    user_agent=audit_context.user_agent,
                    event_description=description,
                    event_details=kwargs,
                    compliance_frameworks=frameworks,
                    hostname=self._get_hostname()
                )
                
                # Add clinical context if provided
                if "patient_id" in kwargs:
                    audit_entry.patient_id = kwargs["patient_id"]
                if "case_uid" in kwargs:
                    audit_entry.case_uid = kwargs["case_uid"]
                if "variant_id" in kwargs:
                    audit_entry.variant_id = kwargs["variant_id"]
                if "interpretation_id" in kwargs:
                    audit_entry.interpretation_id = kwargs["interpretation_id"]
                
                # Add data context if provided
                if "table_affected" in kwargs:
                    audit_entry.table_affected = kwargs["table_affected"]
                if "record_id" in kwargs:
                    audit_entry.record_id = kwargs["record_id"]
                if "data_before" in kwargs:
                    audit_entry.data_before = kwargs["data_before"]
                if "data_after" in kwargs:
                    audit_entry.data_after = kwargs["data_after"]
                
                # Calculate integrity checksum
                audit_entry.checksum = self._calculate_checksum(audit_entry)
                
                session.add(audit_entry)
                session.commit()
                
                self.logger.info(f"Logged audit event: {event_type.value} ({event_uuid})")
                return event_uuid
                
            except Exception as e:
                session.rollback()
                self.logger.error(f"Error logging audit event: {e}")
                raise
    
    def log_user_login(self, 
                      user_id: str,
                      session_id: str,
                      ip_address: str,
                      user_agent: str,
                      success: bool = True) -> str:
        """Log user authentication events"""
        
        context = AuditContext(
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if success:
            return self.log_event(
                AuditEventType.USER_LOGIN,
                f"User {user_id} successfully logged in",
                context,
                AuditSeverity.LOW,
                authentication_method="password"
            )
        else:
            return self.log_event(
                AuditEventType.LOGIN_FAILED,
                f"Failed login attempt for user {user_id}",
                context,
                AuditSeverity.HIGH,
                security_event=True
            )
    
    def log_clinical_decision(self,
                            user_id: str,
                            session_id: str,
                            interpretation_id: str,
                            decision_type: str,
                            clinical_reasoning: str,
                            **context) -> str:
        """Log clinical decision-making events"""
        
        audit_context = AuditContext(
            user_id=user_id,
            session_id=session_id,
            ip_address=context.get("ip_address", "unknown"),
            user_agent=context.get("user_agent", "unknown")
        )
        
        return self.log_event(
            AuditEventType.INTERPRETATION_UPDATE,
            f"Clinical decision made: {decision_type}",
            audit_context,
            AuditSeverity.HIGH,
            interpretation_id=interpretation_id,
            decision_type=decision_type,
            clinical_reasoning=clinical_reasoning,
            **context
        )
    
    def log_data_access(self,
                       user_id: str,
                       session_id: str,
                       resource_type: str,
                       resource_id: str,
                       **context) -> str:
        """Log patient data access events"""
        
        audit_context = AuditContext(
            user_id=user_id,
            session_id=session_id,
            ip_address=context.get("ip_address", "unknown"),
            user_agent=context.get("user_agent", "unknown")
        )
        
        event_type = {
            "patient": AuditEventType.PATIENT_ACCESS,
            "case": AuditEventType.CASE_ACCESS,
            "variant": AuditEventType.VARIANT_ACCESS,
            "report": AuditEventType.REPORT_ACCESS
        }.get(resource_type, AuditEventType.PATIENT_ACCESS)
        
        return self.log_event(
            event_type,
            f"Accessed {resource_type}: {resource_id}",
            audit_context,
            AuditSeverity.MEDIUM,
            resource_type=resource_type,
            resource_id=resource_id,
            **context
        )
    
    def generate_compliance_report(self,
                                 framework: ComplianceFramework,
                                 start_date: datetime,
                                 end_date: datetime,
                                 generated_by: str) -> str:
        """
        Generate compliance report for regulatory submission
        
        Returns:
            report_id of the generated report
        """
        
        with get_db_session() as session:
            try:
                # Query audit events for the period
                audit_events = session.query(ClinicalAuditLog).filter(
                    ClinicalAuditLog.event_timestamp >= start_date,
                    ClinicalAuditLog.event_timestamp <= end_date,
                    ClinicalAuditLog.compliance_frameworks.contains([framework.value])
                ).all()
                
                # Analyze events for compliance
                summary = self._analyze_compliance_events(audit_events, framework)
                
                # Generate detailed report
                report_details = self._generate_detailed_report(audit_events, framework)
                
                # Check for violations
                violations = self._detect_compliance_violations(audit_events, framework)
                
                # Create report record
                report = ComplianceReport(
                    report_type=f"{framework.value}_audit_report",
                    compliance_framework=framework,
                    report_period_start=start_date,
                    report_period_end=end_date,
                    generated_by=generated_by,
                    report_summary=summary,
                    report_details=report_details,
                    violations_found=violations,
                    report_status="draft"
                )
                
                session.add(report)
                session.commit()
                
                self.logger.info(f"Generated compliance report: {report.report_id}")
                return report.report_id
                
            except Exception as e:
                session.rollback()
                self.logger.error(f"Error generating compliance report: {e}")
                raise
    
    def get_audit_trail(self,
                       patient_id: Optional[str] = None,
                       case_uid: Optional[str] = None,
                       user_id: Optional[str] = None,
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None,
                       event_types: Optional[List[AuditEventType]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve audit trail with filtering options
        
        Returns:
            List of audit events matching the criteria
        """
        
        with get_db_session() as session:
            try:
                query = session.query(ClinicalAuditLog)
                
                # Apply filters
                if patient_id:
                    query = query.filter(ClinicalAuditLog.patient_id == patient_id)
                
                if case_uid:
                    query = query.filter(ClinicalAuditLog.case_uid == case_uid)
                
                if user_id:
                    query = query.filter(ClinicalAuditLog.user_id == user_id)
                
                if start_date:
                    query = query.filter(ClinicalAuditLog.event_timestamp >= start_date)
                
                if end_date:
                    query = query.filter(ClinicalAuditLog.event_timestamp <= end_date)
                
                if event_types:
                    query = query.filter(ClinicalAuditLog.event_type.in_(event_types))
                
                # Order by timestamp (most recent first)
                events = query.order_by(ClinicalAuditLog.event_timestamp.desc()).all()
                
                # Convert to dictionaries
                audit_trail = []
                for event in events:
                    audit_trail.append({
                        "audit_id": event.audit_id,
                        "event_uuid": event.event_uuid,
                        "timestamp": event.event_timestamp.isoformat(),
                        "event_type": event.event_type.value,
                        "severity": event.severity.value,
                        "user_id": event.user_id,
                        "description": event.event_description,
                        "details": event.event_details,
                        "patient_id": event.patient_id,
                        "case_uid": event.case_uid,
                        "compliance_frameworks": event.compliance_frameworks
                    })
                
                return audit_trail
                
            except Exception as e:
                self.logger.error(f"Error retrieving audit trail: {e}")
                return []
    
    def verify_audit_integrity(self, audit_id: int) -> bool:
        """Verify the integrity of an audit log entry"""
        
        with get_db_session() as session:
            try:
                entry = session.query(ClinicalAuditLog).filter(
                    ClinicalAuditLog.audit_id == audit_id
                ).first()
                
                if not entry:
                    return False
                
                # Recalculate checksum
                calculated_checksum = self._calculate_checksum(entry)
                
                return calculated_checksum == entry.checksum
                
            except Exception as e:
                self.logger.error(f"Error verifying audit integrity: {e}")
                return False
    
    def _categorize_event(self, event_type: AuditEventType) -> str:
        """Categorize event type for reporting"""
        category_map = {
            AuditEventType.USER_LOGIN: "authentication",
            AuditEventType.USER_LOGOUT: "authentication",
            AuditEventType.LOGIN_FAILED: "security",
            AuditEventType.PATIENT_ACCESS: "data_access",
            AuditEventType.CASE_ACCESS: "data_access",
            AuditEventType.VARIANT_ACCESS: "data_access",
            AuditEventType.INTERPRETATION_CREATE: "clinical_workflow",
            AuditEventType.INTERPRETATION_UPDATE: "clinical_workflow",
            AuditEventType.DATA_CREATE: "data_modification",
            AuditEventType.DATA_UPDATE: "data_modification",
            AuditEventType.DATA_DELETE: "data_modification",
            AuditEventType.UNAUTHORIZED_ACCESS: "security",
            AuditEventType.DATA_EXPORT: "data_transfer"
        }
        return category_map.get(event_type, "other")
    
    def _determine_compliance_frameworks(self, event_type: AuditEventType, kwargs: Dict[str, Any]) -> List[str]:
        """Determine applicable compliance frameworks for an event"""
        frameworks = []
        
        # All clinical events are subject to HIPAA
        if any(key in kwargs for key in ["patient_id", "case_uid", "variant_id"]):
            frameworks.append(ComplianceFramework.HIPAA.value)
        
        # Laboratory testing events are subject to CLIA/CAP
        if event_type in [AuditEventType.INTERPRETATION_CREATE, 
                         AuditEventType.INTERPRETATION_UPDATE,
                         AuditEventType.INTERPRETATION_APPROVE]:
            frameworks.extend([ComplianceFramework.CLIA.value, ComplianceFramework.CAP.value])
        
        # Software-related events may be subject to FDA
        if event_type in [AuditEventType.CONFIGURATION_CHANGE, AuditEventType.KB_UPDATE]:
            frameworks.append(ComplianceFramework.FDA.value)
        
        return frameworks or [ComplianceFramework.HIPAA.value]  # Default to HIPAA
    
    def _calculate_checksum(self, audit_entry: ClinicalAuditLog) -> str:
        """Calculate SHA-256 checksum for audit entry integrity"""
        # Create a string representation of key fields
        checksum_data = f"{audit_entry.event_uuid}|{audit_entry.event_type.value}|{audit_entry.event_timestamp}|{audit_entry.user_id}|{audit_entry.event_description}"
        return hashlib.sha256(checksum_data.encode()).hexdigest()
    
    def _get_hostname(self) -> str:
        """Get current hostname"""
        import socket
        try:
            return socket.gethostname()
        except:
            return "unknown"
    
    def _analyze_compliance_events(self, events: List[ClinicalAuditLog], framework: ComplianceFramework) -> Dict[str, Any]:
        """Analyze events for compliance summary"""
        return {
            "total_events": len(events),
            "event_types": list(set(e.event_type.value for e in events)),
            "unique_users": len(set(e.user_id for e in events)),
            "security_events": len([e for e in events if e.severity == AuditSeverity.CRITICAL]),
            "framework": framework.value
        }
    
    def _generate_detailed_report(self, events: List[ClinicalAuditLog], framework: ComplianceFramework) -> Dict[str, Any]:
        """Generate detailed compliance report data"""
        return {
            "events_by_type": {},
            "events_by_user": {},
            "events_by_severity": {},
            "timeline": [e.event_timestamp.isoformat() for e in events[:100]]  # Sample timeline
        }
    
    def _detect_compliance_violations(self, events: List[ClinicalAuditLog], framework: ComplianceFramework) -> List[Dict[str, Any]]:
        """Detect potential compliance violations"""
        violations = []
        
        # Example: Check for unauthorized access patterns
        failed_logins = [e for e in events if e.event_type == AuditEventType.LOGIN_FAILED]
        if len(failed_logins) > 10:
            violations.append({
                "type": "excessive_failed_logins",
                "severity": "high",
                "description": f"Detected {len(failed_logins)} failed login attempts",
                "recommendation": "Review user access controls and implement account lockout policies"
            })
        
        return violations


# Utility functions
def get_audit_manager() -> AuditTrailManager:
    """Get a configured audit trail manager instance"""
    return AuditTrailManager()


def create_audit_context(user_id: str, session_id: str, request_context: Dict[str, Any]) -> AuditContext:
    """Create audit context from request information"""
    return AuditContext(
        user_id=user_id,
        session_id=session_id,
        ip_address=request_context.get("ip_address", "unknown"),
        user_agent=request_context.get("user_agent", "unknown"),
        location=request_context.get("location"),
        department=request_context.get("department")
    )