"""
Canned Text Management System for Phase 3A Database

This module provides tools to:
1. Load canned text from various sources (files, URLs, APIs)
2. Handle versioning and updates
3. Maintain audit trails
4. Support multiple template types and knowledge bases
"""

from datetime import datetime
from typing import List, Dict, Optional, Any, Union
from pathlib import Path
import json
import requests
import gzip
import csv
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .models import AuditLog, AuditAction
from .expanded_models import (
    TextTemplate, TextTemplateType, GeneratedText,
    CitationSource, SourceReliability
)


class CannedTextSource(str, Enum):
    """Supported knowledge base sources for canned text"""
    ACMG_SF = "ACMG Secondary Findings"
    CLINVAR = "ClinVar"
    ONCOKB = "OncoKB"
    COSMIC = "COSMIC"
    MITELMAN = "Mitelman Database"
    INTERNAL = "Internal Curation"
    CUSTOM = "Custom"


class CannedTextLoader:
    """Base class for loading canned text from various sources"""
    
    def __init__(self, session: Session):
        self.session = session
        self.loaded_count = 0
        self.updated_count = 0
        self.error_count = 0
        self.audit_entries = []
    
    def create_audit_entry(self, action: str, entity_type: str, entity_id: str, 
                          old_values: Dict = None, new_values: Dict = None) -> AuditLog:
        """Create audit log entry for tracking changes"""
        audit = AuditLog(
            table_name=entity_type,
            record_id=entity_id,
            action=AuditAction.INSERT if action == "create" else AuditAction.UPDATE,
            old_values=old_values,
            new_values=new_values,
            user_id="canned_text_loader",
            session_id=f"load_{datetime.utcnow().isoformat()}"
        )
        self.audit_entries.append(audit)
        return audit
    
    def version_template(self, existing_template: TextTemplate, new_version: str) -> TextTemplate:
        """Create new version of template while preserving old version"""
        # Mark existing as deprecated
        existing_template.is_active = False
        existing_template.deprecated_at = datetime.utcnow()
        
        # Record audit entry for deprecation
        self.create_audit_entry(
            "update", "text_templates", existing_template.template_id,
            old_values={"is_active": True, "deprecated_at": None},
            new_values={"is_active": False, "deprecated_at": existing_template.deprecated_at}
        )
        
        return existing_template
    
    def load_from_file(self, file_path: Path, template_type: TextTemplateType,
                      source: CannedTextSource, version: str) -> Dict[str, Any]:
        """Generic file loader - to be implemented by subclasses"""
        raise NotImplementedError
    
    def load_from_url(self, url: str, template_type: TextTemplateType,
                     source: CannedTextSource, version: str) -> Dict[str, Any]:
        """Load canned text from URL"""
        response = requests.get(url)
        response.raise_for_status()
        
        # Save to temp file and process
        temp_path = Path(f"/tmp/{source.value}_{version}.txt")
        temp_path.write_text(response.text)
        
        return self.load_from_file(temp_path, template_type, source, version)
    
    def commit_changes(self) -> Dict[str, int]:
        """Commit all changes and audit entries"""
        # Add audit entries
        for audit in self.audit_entries:
            self.session.add(audit)
        
        # Commit transaction
        self.session.commit()
        
        return {
            "loaded": self.loaded_count,
            "updated": self.updated_count,
            "errors": self.error_count,
            "audit_entries": len(self.audit_entries)
        }


class ACMGSecondaryFindingsLoader(CannedTextLoader):
    """Loader for ACMG Secondary Findings gene list"""
    
    def load_from_file(self, file_path: Path, template_type: TextTemplateType,
                      source: CannedTextSource, version: str) -> Dict[str, Any]:
        """Load ACMG SF gene list and create templates"""
        
        templates_created = []
        
        with open(file_path, 'r') as f:
            # Skip header
            header = f.readline().strip().split('\t')
            
            for line in f:
                fields = line.strip().split('\t')
                if len(fields) < 8:
                    continue
                
                gene = fields[0]
                gene_mim = fields[1]
                disease = fields[2]
                disorder_mim = fields[3]
                category = fields[4]
                inheritance = fields[5]
                sf_version = fields[6]
                variants_to_report = fields[7]
                
                # Check if template exists for this gene
                existing = self.session.query(TextTemplate).filter(
                    and_(
                        TextTemplate.template_type == TextTemplateType.INCIDENTAL_SECONDARY_FINDINGS,
                        TextTemplate.template_name == f"ACMG_SF_{gene}",
                        TextTemplate.is_active == True
                    )
                ).first()
                
                # Create template content
                template_content = f"""
The {gene} gene has been identified as a secondary finding according to ACMG SF v{version} guidelines.

Gene: {gene} (MIM: {gene_mim})
Associated Condition: {disease} (MIM: {disorder_mim})
Phenotype Category: {category}
Inheritance Pattern: {inheritance}
Variants to Report: {variants_to_report}

This finding was not related to the primary indication for testing but represents medically actionable 
information. The ACMG recommends reporting pathogenic and likely pathogenic variants in this gene 
because early intervention or surveillance can significantly impact clinical outcomes.

Genetic counseling is strongly recommended to discuss the implications of this finding for the patient 
and their family members. Additional clinical evaluation may be warranted based on this result.
                """.strip()
                
                if existing:
                    # Version the existing template
                    self.version_template(existing, version)
                    self.updated_count += 1
                
                # Create new template
                new_template = TextTemplate(
                    template_name=f"ACMG_SF_{gene}",
                    template_type=TextTemplateType.INCIDENTAL_SECONDARY_FINDINGS,
                    version=version,
                    template_content=template_content,
                    required_fields=["gene", "variant", "classification"],
                    optional_fields=["vaf", "coverage", "zygosity"],
                    confidence_factors={
                        "classification": 0.4,
                        "coverage": 0.2,
                        "vaf": 0.2,
                        "gene": 0.2
                    },
                    cancer_types=["germline"],  # Not cancer-specific
                    guideline_frameworks=["AMP_ACMG"],
                    is_active=True,
                    parent_template_id=existing.template_id if existing else None,
                    created_by="acmg_sf_loader"
                )
                
                self.session.add(new_template)
                templates_created.append(new_template)
                self.loaded_count += 1
                
                # Create audit entry
                self.create_audit_entry(
                    "create", "text_templates", new_template.template_id,
                    new_values={
                        "template_name": new_template.template_name,
                        "version": version,
                        "source": "ACMG SF"
                    }
                )
        
        # Create or update citation source
        citation_source = self.session.query(CitationSource).filter_by(
            source_name="ACMG Secondary Findings"
        ).first()
        
        if not citation_source:
            citation_source = CitationSource(
                source_id=f"acmg_sf_{version}",
                source_name="ACMG Secondary Findings",
                source_type="guideline",
                reliability_tier=SourceReliability.TIER_2_GUIDELINES,
                citation_format=f"ACMG SF v{version} Gene List",
                url_pattern="https://www.acmg.net/ACMG/Medical-Genetics-Practice-Resources/",
                quality_score=1.0
            )
            self.session.add(citation_source)
        
        return {
            "source": "ACMG SF",
            "version": version,
            "templates_created": len(templates_created),
            "status": "success"
        }


class ChromosomalAlterationLoader(CannedTextLoader):
    """Loader for Mitelman chromosomal alteration interpretations"""
    
    def load_from_file(self, file_path: Path, template_type: TextTemplateType,
                      source: CannedTextSource, version: str) -> Dict[str, Any]:
        """Load Mitelman database chromosomal alterations from CSV"""
        
        templates_created = []
        seen_alterations = set()  # Track unique alteration patterns
        
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                morph_name = row.get('MorphName', '')
                event_type = row.get('EventType', '')
                event = row.get('Event', '')
                gene = row.get('Gene', '')
                case_count = row.get('CaseCount', '')
                event_class = row.get('Type', '')  # U/B/T
                grch38_pos = row.get('GRCh38_Pos', '')
                
                if not morph_name or not event:
                    continue
                
                # Skip fusion events as they're gene-level, not chromosomal
                if event_type == 'Fusion':
                    continue
                
                # Create unique key for this alteration pattern
                alteration_key = f"{morph_name}_{event}"
                if alteration_key in seen_alterations:
                    continue
                seen_alterations.add(alteration_key)
                
                # Create template name
                safe_event = event.replace('(', '').replace(')', '').replace(';', '_')
                template_name = f"CHR_ALT_{safe_event}_{morph_name.replace(' ', '_')[:30]}"
                
                # Check for existing
                existing = self.session.query(TextTemplate).filter(
                    and_(
                        TextTemplate.template_type == TextTemplateType.CHROMOSOMAL_ALTERATION_INTERPRETATION,
                        TextTemplate.template_name == template_name,
                        TextTemplate.is_active == True
                    )
                ).first()
                
                # Determine event type description
                event_type_desc = {
                    'U': 'unbalanced',
                    'B': 'balanced',
                    'T': 'translocation'
                }.get(event_class, 'chromosomal')
                
                # Create template content
                template_content = f"""
Chromosomal Alteration: {event}

This {event_type_desc} chromosomal abnormality has been documented in {morph_name} based on 
the Mitelman Database of Chromosome Aberrations and Gene Fusions in Cancer.

Event Details:
- Alteration: {event}
- Type: {event_type} ({event_type_desc})
"""
                if gene:
                    template_content += f"- Associated Gene(s): {gene}\n"
                
                if case_count and case_count.isdigit():
                    template_content += f"- Reported Cases: {case_count}\n"
                
                if grch38_pos:
                    template_content += f"- Genomic Coordinates (GRCh38): {grch38_pos}\n"
                
                template_content += """
Clinical Significance: 
"""
                
                # Add specific interpretations based on common alterations
                if 'del(5q)' in event or 'del(7q)' in event:
                    template_content += """
This deletion is commonly associated with myeloid malignancies and may indicate a more 
aggressive disease course. Additional molecular characterization is recommended.
"""
                elif 't(9;22)' in event and 'BCR::ABL1' in gene:
                    template_content += """
The Philadelphia chromosome t(9;22) resulting in BCR::ABL1 fusion is a defining feature 
with established targeted therapy options using tyrosine kinase inhibitors.
"""
                elif 't(15;17)' in event:
                    template_content += """
This translocation is pathognomonic for acute promyelocytic leukemia (APL) and indicates 
eligibility for ATRA/ATO therapy with excellent prognosis when treated appropriately.
"""
                elif 'inv(16)' in event or 't(16;16)' in event:
                    template_content += """
This alteration defines core binding factor AML with generally favorable prognosis. 
Standard intensive chemotherapy with high-dose cytarabine consolidation is indicated.
"""
                else:
                    template_content += """
This chromosomal alteration may have diagnostic, prognostic, or therapeutic implications 
specific to the cancer type. Correlation with morphology, immunophenotype, and molecular 
findings is recommended for comprehensive assessment.
"""
                
                template_content = template_content.strip()
                
                if existing:
                    self.version_template(existing, version)
                    self.updated_count += 1
                
                # Create new template
                new_template = TextTemplate(
                    template_name=template_name,
                    template_type=TextTemplateType.CHROMOSOMAL_ALTERATION_INTERPRETATION,
                    version=version,
                    template_content=template_content,
                    required_fields=["karyotype", "cancer_type"],
                    optional_fields=["cell_percentage", "clone_size", "additional_abnormalities"],
                    confidence_factors={
                        "karyotype_match": 0.5,
                        "cancer_type_match": 0.3,
                        "clone_size": 0.2
                    },
                    cancer_types=[morph_name],
                    guideline_frameworks=["AMP_ACMG", "CGC_VICC"],
                    is_active=True,
                    parent_template_id=existing.template_id if existing else None,
                    created_by="mitelman_loader"
                )
                
                self.session.add(new_template)
                templates_created.append(new_template)
                self.loaded_count += 1
                
                # Create audit entry
                self.create_audit_entry(
                    "create", "text_templates", new_template.template_id,
                    new_values={
                        "template_name": new_template.template_name,
                        "version": version,
                        "source": "Mitelman Database"
                    }
                )
        
        return {
            "source": "Mitelman Database",
            "version": version,
            "templates_created": len(templates_created),
            "status": "success"
        }


class GeneralGeneInfoLoader(CannedTextLoader):
    """Loader for general gene information from multiple sources"""
    
    def load_oncokb_genes(self, file_path: Path, version: str) -> int:
        """Load gene info from OncoKB cancer gene list"""
        count = 0
        
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f, delimiter='\t')
            
            for row in reader:
                gene = row['Hugo Symbol']
                is_oncogene = row.get('Is Oncogene', 'No') == 'Yes'
                is_tsg = row.get('Is Tumor Suppressor Gene', 'No') == 'Yes'
                aliases = row.get('Gene Aliases', '')
                
                # Create gene description
                gene_type = []
                if is_oncogene:
                    gene_type.append("oncogene")
                if is_tsg:
                    gene_type.append("tumor suppressor gene")
                
                gene_type_str = " and ".join(gene_type) if gene_type else "cancer-associated gene"
                
                template_content = f"""
{gene} is a {gene_type_str} included in the OncoKB Cancer Gene List.

Gene Symbol: {gene}
"""
                if aliases:
                    template_content += f"Gene Aliases: {aliases}\n"
                
                template_content += f"""
Classification: {'Oncogene' if is_oncogene else ''}{'/' if is_oncogene and is_tsg else ''}{'Tumor Suppressor' if is_tsg else ''}

This gene has been identified as clinically relevant in cancer based on OncoKB's comprehensive 
curation of cancer genes. Alterations in this gene may have diagnostic, prognostic, or 
therapeutic implications depending on the specific variant and cancer type.
                """.strip()
                
                # Create template
                new_template = TextTemplate(
                    template_name=f"GENE_INFO_{gene}",
                    template_type=TextTemplateType.GENERAL_GENE_INFO,
                    version=version,
                    template_content=template_content,
                    required_fields=["gene"],
                    optional_fields=["variant_count", "cancer_type"],
                    cancer_types=["pan-cancer"],
                    guideline_frameworks=["ONCOKB"],
                    is_active=True,
                    created_by="oncokb_gene_loader"
                )
                
                self.session.add(new_template)
                count += 1
        
        return count
    
    def load_clinvar_genes(self, file_path: Path, version: str) -> int:
        """Load gene summaries from ClinVar"""
        count = 0
        
        # Handle gzipped file
        opener = gzip.open if file_path.suffix == '.gz' else open
        
        with opener(file_path, 'rt') as f:
            # Skip header
            header = f.readline()
            
            for line in f:
                fields = line.strip().split('\t')
                if len(fields) < 5:
                    continue
                
                gene = fields[0]
                gene_id = fields[1]
                total_submissions = int(fields[2]) if fields[2].isdigit() else 0
                p_lp_count = int(fields[3]) if fields[3].isdigit() else 0
                
                # Only create templates for genes with significant clinical data
                if total_submissions < 10:
                    continue
                
                template_content = f"""
{gene} has extensive clinical variant data in ClinVar with {total_submissions:,} total submissions.

Gene Symbol: {gene}
Gene ID: {gene_id}
Pathogenic/Likely Pathogenic Variants: {p_lp_count:,}

This gene has been extensively studied in clinical contexts based on ClinVar submissions. 
The clinical significance of variants in this gene should be interpreted based on specific 
variant data and clinical context.
                """.strip()
                
                # Check if we already have a template for this gene
                existing = self.session.query(TextTemplate).filter(
                    and_(
                        TextTemplate.template_type == TextTemplateType.GENERAL_GENE_INFO,
                        TextTemplate.template_name == f"GENE_INFO_{gene}",
                        TextTemplate.is_active == True
                    )
                ).first()
                
                if existing:
                    # Enhance existing template with ClinVar data
                    existing.template_content += f"\n\nClinVar Data:\n{template_content}"
                    self.updated_count += 1
                else:
                    # Create new template
                    new_template = TextTemplate(
                        template_name=f"GENE_INFO_{gene}",
                        template_type=TextTemplateType.GENERAL_GENE_INFO,
                        version=version,
                        template_content=template_content,
                        required_fields=["gene"],
                        optional_fields=["variant_count", "clinical_significance"],
                        guideline_frameworks=["AMP_ACMG"],
                        is_active=True,
                        created_by="clinvar_gene_loader"
                    )
                    
                    self.session.add(new_template)
                    count += 1
        
        return count
    
    def load_from_file(self, file_path: Path, template_type: TextTemplateType,
                      source: CannedTextSource, version: str) -> Dict[str, Any]:
        """Load general gene info from multiple sources"""
        
        total_count = 0
        
        # Load from different sources based on file type
        if "OncoKb" in str(file_path):
            total_count += self.load_oncokb_genes(file_path, version)
        elif "gene_specific_summary" in str(file_path):
            total_count += self.load_clinvar_genes(file_path, version)
        
        self.loaded_count = total_count
        
        return {
            "source": source.value,
            "version": version,
            "templates_created": total_count,
            "status": "success"
        }


class CannedTextManager:
    """Main interface for managing canned text in the database"""
    
    def __init__(self, session: Session):
        self.session = session
        self.loaders = {
            CannedTextSource.ACMG_SF: ACMGSecondaryFindingsLoader(session),
            CannedTextSource.MITELMAN: ChromosomalAlterationLoader(session),
            CannedTextSource.ONCOKB: GeneralGeneInfoLoader(session),
            CannedTextSource.CLINVAR: GeneralGeneInfoLoader(session)
        }
    
    def update_canned_text(self, 
                          template_type: TextTemplateType,
                          source: CannedTextSource,
                          source_path: Union[str, Path],
                          version: str,
                          is_url: bool = False) -> Dict[str, Any]:
        """
        Update canned text in database from file or URL
        
        Args:
            template_type: Type of template to create
            source: Knowledge base source
            source_path: File path or URL
            version: Version identifier (e.g., "3.3" for ACMG SF)
            is_url: Whether source_path is a URL
            
        Returns:
            Dictionary with update results
        """
        
        # Get appropriate loader
        loader = self.loaders.get(source)
        if not loader:
            raise ValueError(f"No loader available for source: {source}")
        
        # Record start time
        start_time = datetime.utcnow()
        
        try:
            # Load from URL or file
            if is_url:
                result = loader.load_from_url(source_path, template_type, source, version)
            else:
                result = loader.load_from_file(Path(source_path), template_type, source, version)
            
            # Commit changes
            commit_result = loader.commit_changes()
            
            # Create master audit entry for this update
            master_audit = AuditLog(
                table_name="canned_text_update",
                record_id=f"{source.value}_{version}",
                action=AuditAction.INSERT,
                new_values={
                    "source": source.value,
                    "template_type": template_type.value,
                    "version": version,
                    "source_path": str(source_path),
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "templates_loaded": commit_result["loaded"],
                    "templates_updated": commit_result["updated"],
                    "errors": commit_result["errors"]
                },
                user_id="canned_text_manager",
                session_id=f"update_{source.value}_{version}"
            )
            self.session.add(master_audit)
            self.session.commit()
            
            return {
                "status": "success",
                "source": source.value,
                "version": version,
                "results": commit_result,
                "duration": (datetime.utcnow() - start_time).total_seconds()
            }
            
        except Exception as e:
            self.session.rollback()
            
            # Log error
            error_audit = AuditLog(
                table_name="canned_text_update_error",
                record_id=f"{source.value}_{version}",
                action=AuditAction.INSERT,
                new_values={
                    "source": source.value,
                    "template_type": template_type.value,
                    "version": version,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                },
                user_id="canned_text_manager"
            )
            self.session.add(error_audit)
            self.session.commit()
            
            return {
                "status": "error",
                "source": source.value,
                "version": version,
                "error": str(e)
            }
    
    def get_version_history(self, template_type: TextTemplateType, 
                           source: Optional[CannedTextSource] = None) -> List[Dict]:
        """Get version history for templates"""
        
        query = self.session.query(TextTemplate).filter(
            TextTemplate.template_type == template_type
        )
        
        if source:
            # Filter by source in template name or created_by
            query = query.filter(
                or_(
                    TextTemplate.created_by.contains(source.value.lower()),
                    TextTemplate.template_name.contains(source.value.upper())
                )
            )
        
        templates = query.order_by(
            TextTemplate.template_name,
            TextTemplate.version.desc()
        ).all()
        
        # Group by template name to show version history
        history = {}
        for template in templates:
            if template.template_name not in history:
                history[template.template_name] = []
            
            history[template.template_name].append({
                "version": template.version,
                "active": template.is_active,
                "created_at": template.created_at.isoformat(),
                "deprecated_at": template.deprecated_at.isoformat() if template.deprecated_at else None,
                "usage_count": template.usage_count
            })
        
        return history
    
    def get_update_history(self, days: int = 30) -> List[Dict]:
        """Get recent canned text update history"""
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        updates = self.session.query(AuditLog).filter(
            and_(
                AuditLog.table_name == "canned_text_update",
                AuditLog.timestamp >= cutoff
            )
        ).order_by(AuditLog.timestamp.desc()).all()
        
        return [{
            "source": update.new_values.get("source"),
            "version": update.new_values.get("version"),
            "template_type": update.new_values.get("template_type"),
            "timestamp": update.timestamp.isoformat(),
            "templates_loaded": update.new_values.get("templates_loaded"),
            "templates_updated": update.new_values.get("templates_updated"),
            "duration": update.new_values.get("duration")
        } for update in updates]


# Convenience functions for common updates

def update_acmg_sf(session: Session, version: str, file_path: str) -> Dict:
    """Update ACMG Secondary Findings templates"""
    manager = CannedTextManager(session)
    return manager.update_canned_text(
        TextTemplateType.INCIDENTAL_SECONDARY_FINDINGS,
        CannedTextSource.ACMG_SF,
        file_path,
        version
    )


def update_chromosomal_alterations(session: Session, version: str, file_path: str) -> Dict:
    """Update Mitelman chromosomal alteration templates"""
    manager = CannedTextManager(session)
    return manager.update_canned_text(
        TextTemplateType.CHROMOSOMAL_ALTERATION_INTERPRETATION,
        CannedTextSource.MITELMAN,
        file_path,
        version
    )


def update_gene_info_from_oncokb(session: Session, version: str, file_path: str) -> Dict:
    """Update general gene info from OncoKB"""
    manager = CannedTextManager(session)
    return manager.update_canned_text(
        TextTemplateType.GENERAL_GENE_INFO,
        CannedTextSource.ONCOKB,
        file_path,
        version
    )


def update_gene_info_from_clinvar(session: Session, version: str, file_path: str) -> Dict:
    """Update general gene info from ClinVar"""
    manager = CannedTextManager(session)
    return manager.update_canned_text(
        TextTemplateType.GENERAL_GENE_INFO,
        CannedTextSource.CLINVAR,
        file_path,
        version
    )


if __name__ == "__main__":
    # Example usage
    from datetime import timedelta
    from .base import get_session
    
    session = get_session()
    manager = CannedTextManager(session)
    
    # Update ACMG SF to version 3.3
    result = manager.update_canned_text(
        TextTemplateType.INCIDENTAL_SECONDARY_FINDINGS,
        CannedTextSource.ACMG_SF,
        "/Users/lauferva/Desktop/Arti/.refs/secondary_findings/acmg_sf/ACMG_SF_v3.2.txt",
        "3.2"
    )
    print(f"ACMG SF Update: {result}")
    
    # Get version history
    history = manager.get_version_history(
        TextTemplateType.INCIDENTAL_SECONDARY_FINDINGS,
        CannedTextSource.ACMG_SF
    )
    print(f"Version History: {json.dumps(history, indent=2)}")