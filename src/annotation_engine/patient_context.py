"""
Patient Context Management

Manages patient and case metadata, OncoTree disease validation,
and clinical context for variant interpretation.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class TissueType(str, Enum):
    """Major tissue types for OncoTree mapping"""
    BLOOD = "Blood"
    BONE = "Bone"
    BRAIN = "Brain/Nervous System"
    BREAST = "Breast"
    CERVIX = "Cervix"
    COLORECTAL = "Bowel"
    EYE = "Eye"
    HEAD_NECK = "Head and Neck"
    KIDNEY = "Kidney"
    LIVER = "Liver"
    LUNG = "Lung/Pleura"
    LYMPH = "Lymphoid"
    MYELOID = "Myeloid"
    OVARY = "Ovary/Fallopian Tube"
    PANCREAS = "Pancreas"
    PENIS = "Penis"
    PERIPHERAL_NERVOUS = "Peripheral Nervous System"
    PERITONEUM = "Peritoneum"
    PROSTATE = "Prostate"
    SKIN = "Skin"
    SOFT_TISSUE = "Soft Tissue"
    STOMACH = "Stomach/Esophagus"
    TESTIS = "Testis"
    THYMUS = "Thymus"
    THYROID = "Thyroid"
    UTERUS = "Uterus"
    VULVA_VAGINA = "Vulva/Vagina"
    OTHER = "Other"


@dataclass
class PatientContext:
    """Complete patient and case context"""
    patient_uid: str
    case_uid: str
    cancer_type: str
    oncotree_code: Optional[str] = None
    tissue_type: Optional[TissueType] = None
    primary_site: Optional[str] = None
    metastatic_site: Optional[str] = None
    stage: Optional[str] = None
    grade: Optional[str] = None
    age_at_diagnosis: Optional[int] = None
    sex: Optional[str] = None
    prior_therapies: List[str] = field(default_factory=list)
    family_history: bool = False
    germline_findings: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, any] = field(default_factory=dict)


class OncoTreeValidator:
    """Validates and maps OncoTree disease codes"""
    
    # Common OncoTree codes and their descriptions
    # This is a subset - in production, load from full OncoTree JSON
    ONCOTREE_CODES = {
        # Lung
        "LUAD": {"name": "Lung Adenocarcinoma", "tissue": TissueType.LUNG, "parent": "NSCLC"},
        "LUSC": {"name": "Lung Squamous Cell Carcinoma", "tissue": TissueType.LUNG, "parent": "NSCLC"},
        "SCLC": {"name": "Small Cell Lung Cancer", "tissue": TissueType.LUNG, "parent": "LUNG"},
        "NSCLC": {"name": "Non-Small Cell Lung Cancer", "tissue": TissueType.LUNG, "parent": "LUNG"},
        
        # Breast
        "BRCA": {"name": "Invasive Breast Carcinoma", "tissue": TissueType.BREAST, "parent": "BREAST"},
        "IDC": {"name": "Breast Invasive Ductal Carcinoma", "tissue": TissueType.BREAST, "parent": "BRCA"},
        "ILC": {"name": "Breast Invasive Lobular Carcinoma", "tissue": TissueType.BREAST, "parent": "BRCA"},
        "TNBC": {"name": "Triple-Negative Breast Cancer", "tissue": TissueType.BREAST, "parent": "BRCA"},
        
        # Colorectal
        "COAD": {"name": "Colon Adenocarcinoma", "tissue": TissueType.COLORECTAL, "parent": "BOWEL"},
        "READ": {"name": "Rectum Adenocarcinoma", "tissue": TissueType.COLORECTAL, "parent": "BOWEL"},
        "COADREAD": {"name": "Colorectal Adenocarcinoma", "tissue": TissueType.COLORECTAL, "parent": "BOWEL"},
        
        # Melanoma
        "MEL": {"name": "Melanoma", "tissue": TissueType.SKIN, "parent": "SKIN"},
        "SKCM": {"name": "Cutaneous Melanoma", "tissue": TissueType.SKIN, "parent": "MEL"},
        "ACRM": {"name": "Acral Melanoma", "tissue": TissueType.SKIN, "parent": "MEL"},
        "DESM": {"name": "Desmoplastic Melanoma", "tissue": TissueType.SKIN, "parent": "MEL"},
        
        # Prostate
        "PRAD": {"name": "Prostate Adenocarcinoma", "tissue": TissueType.PROSTATE, "parent": "PROSTATE"},
        "NEPC": {"name": "Neuroendocrine Prostate Cancer", "tissue": TissueType.PROSTATE, "parent": "PROSTATE"},
        
        # Pancreas
        "PAAD": {"name": "Pancreatic Adenocarcinoma", "tissue": TissueType.PANCREAS, "parent": "PANCREAS"},
        "PNET": {"name": "Pancreatic Neuroendocrine Tumor", "tissue": TissueType.PANCREAS, "parent": "PANCREAS"},
        
        # Brain
        "GBM": {"name": "Glioblastoma Multiforme", "tissue": TissueType.BRAIN, "parent": "DIFFG"},
        "LGG": {"name": "Low-Grade Glioma", "tissue": TissueType.BRAIN, "parent": "DIFFG"},
        "DIFFG": {"name": "Diffuse Glioma", "tissue": TissueType.BRAIN, "parent": "BRAIN"},
        
        # Blood
        "AML": {"name": "Acute Myeloid Leukemia", "tissue": TissueType.MYELOID, "parent": "LEUK"},
        "ALL": {"name": "Acute Lymphoblastic Leukemia", "tissue": TissueType.LYMPH, "parent": "LEUK"},
        "CLL": {"name": "Chronic Lymphocytic Leukemia", "tissue": TissueType.LYMPH, "parent": "LEUK"},
        "DLBCL": {"name": "Diffuse Large B-Cell Lymphoma", "tissue": TissueType.LYMPH, "parent": "NHL"},
        
        # Other common types
        "OV": {"name": "Ovarian Cancer", "tissue": TissueType.OVARY, "parent": "OVARY"},
        "HGSOC": {"name": "High-Grade Serous Ovarian Cancer", "tissue": TissueType.OVARY, "parent": "OV"},
        "KIRC": {"name": "Kidney Clear Cell Carcinoma", "tissue": TissueType.KIDNEY, "parent": "RCC"},
        "HCC": {"name": "Hepatocellular Carcinoma", "tissue": TissueType.LIVER, "parent": "LIVER"},
        "BLCA": {"name": "Bladder Urothelial Carcinoma", "tissue": TissueType.OTHER, "parent": "BLADDER"},
        "ESCA": {"name": "Esophageal Carcinoma", "tissue": TissueType.STOMACH, "parent": "STOMACH"},
        "STAD": {"name": "Stomach Adenocarcinoma", "tissue": TissueType.STOMACH, "parent": "STOMACH"},
        "THCA": {"name": "Thyroid Carcinoma", "tissue": TissueType.THYROID, "parent": "THYROID"},
        "UCEC": {"name": "Uterine Corpus Endometrial Carcinoma", "tissue": TissueType.UTERUS, "parent": "UTERUS"},
    }
    
    # Common aliases
    ALIASES = {
        "LUNG_ADENO": "LUAD",
        "LUNG_SQUAMOUS": "LUSC",
        "BREAST": "BRCA",
        "COLON": "COAD",
        "RECTAL": "READ",
        "COLORECTAL": "COADREAD",
        "MELANOMA": "SKCM",
        "PROSTATE": "PRAD",
        "PANCREATIC": "PAAD",
        "GLIOBLASTOMA": "GBM",
        "OVARIAN": "OV",
        "KIDNEY": "KIRC",
        "LIVER": "HCC",
        "BLADDER": "BLCA",
        "ESOPHAGEAL": "ESCA",
        "GASTRIC": "STAD",
        "STOMACH": "STAD",
        "THYROID": "THCA",
        "ENDOMETRIAL": "UCEC",
    }
    
    def __init__(self, oncotree_file: Optional[Path] = None):
        """
        Initialize validator
        
        Args:
            oncotree_file: Optional path to full OncoTree JSON file
        """
        self.oncotree_data = self.ONCOTREE_CODES.copy()
        
        # Load full OncoTree data if provided
        if oncotree_file and oncotree_file.exists():
            try:
                with open(oncotree_file, 'r') as f:
                    full_data = json.load(f)
                    self._parse_oncotree_json(full_data)
            except Exception as e:
                logger.warning(f"Failed to load OncoTree file: {e}")
    
    def validate_code(self, code: str) -> Tuple[bool, Optional[Dict[str, any]]]:
        """
        Validate an OncoTree code
        
        Args:
            code: OncoTree code to validate
            
        Returns:
            Tuple of (is_valid, code_info)
        """
        if not code:
            return False, None
        
        # Convert to uppercase
        code = code.upper()
        
        # Check aliases first
        if code in self.ALIASES:
            code = self.ALIASES[code]
        
        # Look up code
        if code in self.oncotree_data:
            return True, {
                "code": code,
                "name": self.oncotree_data[code]["name"],
                "tissue": self.oncotree_data[code]["tissue"],
                "parent": self.oncotree_data[code].get("parent")
            }
        
        return False, None
    
    def get_tissue_type(self, oncotree_code: str) -> Optional[TissueType]:
        """Get tissue type for an OncoTree code"""
        is_valid, info = self.validate_code(oncotree_code)
        if is_valid and info:
            return info.get("tissue")
        return None
    
    def get_parent_codes(self, oncotree_code: str) -> List[str]:
        """Get all parent codes in the hierarchy"""
        parents = []
        current = oncotree_code.upper()
        
        while current in self.oncotree_data:
            parent = self.oncotree_data[current].get("parent")
            if parent and parent != current:
                parents.append(parent)
                current = parent
            else:
                break
        
        return parents
    
    def get_related_codes(self, oncotree_code: str) -> Set[str]:
        """Get all related codes (parents, children, siblings)"""
        related = set()
        
        # Add self
        code = oncotree_code.upper()
        if code in self.oncotree_data:
            related.add(code)
            
            # Add parents
            related.update(self.get_parent_codes(code))
            
            # Add children
            for other_code, data in self.oncotree_data.items():
                if data.get("parent") == code:
                    related.add(other_code)
            
            # Add siblings (same parent)
            parent = self.oncotree_data[code].get("parent")
            if parent:
                for other_code, data in self.oncotree_data.items():
                    if data.get("parent") == parent:
                        related.add(other_code)
        
        return related
    
    def _parse_oncotree_json(self, data: Dict):
        """Parse full OncoTree JSON format"""
        # This would parse the official OncoTree JSON format
        # For now, using our subset
        pass


class PatientContextManager:
    """Manages patient context creation and validation"""
    
    def __init__(self, oncotree_validator: Optional[OncoTreeValidator] = None):
        self.oncotree_validator = oncotree_validator or OncoTreeValidator()
    
    def create_context(self,
                      patient_uid: str,
                      case_uid: str,
                      cancer_type: str,
                      oncotree_code: Optional[str] = None,
                      **kwargs) -> PatientContext:
        """
        Create a validated patient context
        
        Args:
            patient_uid: Patient identifier
            case_uid: Case identifier
            cancer_type: Cancer type description
            oncotree_code: Optional OncoTree code
            **kwargs: Additional context fields
            
        Returns:
            Validated PatientContext
        """
        # Validate OncoTree code if provided
        tissue_type = None
        if oncotree_code:
            is_valid, code_info = self.oncotree_validator.validate_code(oncotree_code)
            if is_valid:
                tissue_type = code_info["tissue"]
                # Update cancer_type with official name if generic
                if cancer_type.lower() in ["cancer", "tumor", "carcinoma", "unknown"]:
                    cancer_type = code_info["name"]
            else:
                logger.warning(f"Invalid OncoTree code: {oncotree_code}")
                oncotree_code = None
        
        # Create context
        context = PatientContext(
            patient_uid=patient_uid,
            case_uid=case_uid,
            cancer_type=cancer_type,
            oncotree_code=oncotree_code,
            tissue_type=tissue_type,
            **kwargs
        )
        
        return context
    
    def get_cancer_specific_genes(self, context: PatientContext) -> List[str]:
        """
        Get cancer-specific driver genes for the context
        
        Args:
            context: Patient context
            
        Returns:
            List of relevant driver genes
        """
        # This would integrate with cancer gene databases
        # For now, return common drivers based on tissue type
        
        tissue_drivers = {
            TissueType.LUNG: ["EGFR", "KRAS", "ALK", "ROS1", "MET", "BRAF", "RET", "ERBB2"],
            TissueType.BREAST: ["BRCA1", "BRCA2", "ERBB2", "ESR1", "PIK3CA", "AKT1", "PTEN"],
            TissueType.COLORECTAL: ["APC", "KRAS", "BRAF", "PIK3CA", "SMAD4", "TP53", "MSH2", "MLH1"],
            TissueType.SKIN: ["BRAF", "NRAS", "KIT", "NF1", "CDKN2A", "PTEN", "TP53"],
            TissueType.PROSTATE: ["AR", "PTEN", "TP53", "BRCA2", "ATM", "CDK12", "SPOP"],
            TissueType.PANCREAS: ["KRAS", "CDKN2A", "TP53", "SMAD4", "BRCA2", "PALB2", "ATM"],
        }
        
        if context.tissue_type in tissue_drivers:
            return tissue_drivers[context.tissue_type]
        
        # Return pan-cancer drivers as fallback
        return ["TP53", "KRAS", "PIK3CA", "PTEN", "APC", "BRAF", "EGFR", "MYC"]
    
    def get_therapy_implications(self, context: PatientContext) -> Dict[str, List[str]]:
        """
        Get therapy implications based on cancer type
        
        Args:
            context: Patient context
            
        Returns:
            Dict of gene -> approved therapies
        """
        # This would integrate with therapy databases
        # For now, return common associations
        
        therapy_map = {
            "LUAD": {
                "EGFR": ["Osimertinib", "Erlotinib", "Gefitinib", "Afatinib"],
                "ALK": ["Alectinib", "Crizotinib", "Ceritinib", "Lorlatinib"],
                "ROS1": ["Crizotinib", "Entrectinib", "Lorlatinib"],
                "BRAF": ["Dabrafenib + Trametinib"],
                "MET": ["Capmatinib", "Tepotinib"],
                "RET": ["Selpercatinib", "Pralsetinib"],
            },
            "SKCM": {
                "BRAF": ["Vemurafenib", "Dabrafenib", "Encorafenib + Binimetinib"],
                "KIT": ["Imatinib"],
            },
            "COADREAD": {
                "BRAF": ["Encorafenib + Cetuximab"],
                "KRAS": ["Sotorasib", "Adagrasib"],  # G12C specific
                "MSI-H": ["Pembrolizumab", "Nivolumab"],
            },
        }
        
        if context.oncotree_code in therapy_map:
            return therapy_map[context.oncotree_code]
        
        return {}
    
    def validate_context(self, context: PatientContext) -> Tuple[bool, List[str]]:
        """
        Validate a patient context
        
        Args:
            context: PatientContext to validate
            
        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []
        
        # Required fields
        if not context.patient_uid:
            issues.append("Missing patient UID")
        if not context.case_uid:
            issues.append("Missing case UID")
        if not context.cancer_type:
            issues.append("Missing cancer type")
        
        # OncoTree validation
        if context.oncotree_code:
            is_valid, _ = self.oncotree_validator.validate_code(context.oncotree_code)
            if not is_valid:
                issues.append(f"Invalid OncoTree code: {context.oncotree_code}")
        
        # Age validation
        if context.age_at_diagnosis is not None:
            if context.age_at_diagnosis < 0 or context.age_at_diagnosis > 150:
                issues.append(f"Invalid age at diagnosis: {context.age_at_diagnosis}")
        
        # Sex validation
        if context.sex and context.sex.upper() not in ["M", "F", "MALE", "FEMALE", "OTHER", "UNKNOWN"]:
            issues.append(f"Invalid sex value: {context.sex}")
        
        return len(issues) == 0, issues