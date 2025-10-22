"""Enhanced evidence collection service with clothing-based person matching."""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ticket import TicketEvidence
from src.models.person_embeddings import PersonAppearance
from src.services.clothing_analysis_service import ClothingAnalysisService
from src.services.ai.threat_detection_service import ThreatDetectionService
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EnhancedEvidenceCollectionService:
    """Enhanced evidence collection with person identification and matching."""

    def __init__(self, session: AsyncSession):
        """Initialize enhanced evidence collection service."""
        self.session = session
        self.clothing_service = ClothingAnalysisService(session)
        self.threat_service = ThreatDetectionService()

    async def collect_evidence_for_threat(
        self,
        ticket_id: int,
        threat_image_path: str,
        video_id: int,
        frame_timestamp_ms: int,
        processing_id: str,
        threat_assessment: Dict,
        evidence_folder: Path
    ) -> Dict:
        """
        Collect comprehensive evidence for a threat including person identification.
        
        Args:
            ticket_id: Ticket ID
            threat_image_path: Path to threat image
            video_id: Video ID
            frame_timestamp_ms: Frame timestamp
            processing_id: Processing batch ID
            threat_assessment: Threat assessment results
            evidence_folder: Evidence folder path
            
        Returns:
            Evidence collection results
        """
        logger.info(f"Collecting evidence for ticket {ticket_id}")
        
        try:
            evidence_results = {
                'ticket_id': ticket_id,
                'evidence_files': [],
                'related_persons': [],
                'person_analysis': {},
                'status': 'completed'
            }
            
            # 1. Store original threat image
            original_evidence = await self._store_original_threat_image(
                ticket_id, threat_image_path, frame_timestamp_ms, evidence_folder
            )
            if original_evidence:
                evidence_results['evidence_files'].append(original_evidence)
            
            # 2. Analyze persons in threat image
            person_analysis = await self.clothing_service.analyze_person_in_image(
                threat_image_path, video_id, frame_timestamp_ms, processing_id, evidence_folder
            )
            evidence_results['person_analysis'] = person_analysis
            
            # 3. Find related persons based on clothing/appearance
            if person_analysis.get('persons'):
                for person_data in person_analysis['persons']:
                    person_id = person_data['person_identification']['person_id']
                    
                    # Find related persons across all videos
                    related_persons = await self.clothing_service.find_related_persons_for_ticket(
                        ticket_id, person_id, evidence_folder
                    )
                    evidence_results['related_persons'].extend(related_persons)
                    
                    # Store person evidence
                    person_evidence = await self._store_person_evidence(
                        ticket_id, person_data, evidence_folder
                    )
                    if person_evidence:
                        evidence_results['evidence_files'].append(person_evidence)
            
            # 4. Generate comprehensive threat report
            threat_report = await self._generate_threat_report(
                ticket_id, threat_assessment, person_analysis, evidence_results['related_persons']
            )
            
            # Save threat report
            report_path = evidence_folder / "threat_report.txt"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(threat_report)
            
            evidence_results['threat_report_path'] = str(report_path)
            evidence_results['total_evidence_files'] = len(evidence_results['evidence_files'])
            
            logger.info(
                f"Evidence collection completed for ticket {ticket_id}: "
                f"{len(evidence_results['evidence_files'])} files, "
                f"{len(evidence_results['related_persons'])} related persons"
            )
            
            return evidence_results
            
        except Exception as e:
            logger.error(f"Evidence collection failed for ticket {ticket_id}: {e}", exc_info=True)
            return {
                'ticket_id': ticket_id,
                'evidence_files': [],
                'related_persons': [],
                'person_analysis': {},
                'status': 'failed',
                'error': str(e)
            }

    async def _store_original_threat_image(
        self,
        ticket_id: int,
        image_path: str,
        frame_timestamp_ms: int,
        evidence_folder: Path
    ) -> Optional[Dict]:
        """Store original threat image as evidence."""
        try:
            # Generate filename
            filename = f"original_threat_{frame_timestamp_ms}ms.jpg"
            evidence_path = evidence_folder / filename
            
            # Copy image
            shutil.copy2(image_path, evidence_path)
            
            # Create evidence record
            evidence = TicketEvidence(
                ticket_id=ticket_id,
                storage_file_id=0,  # Will be updated when file is registered
                evidence_type="original",
                file_path=str(evidence_path),
                file_name=filename,
                source_video_id=None,  # Will be set by caller
                frame_timestamp_ms=frame_timestamp_ms,
                description="Original threat detection image"
            )
            
            self.session.add(evidence)
            await self.session.flush()
            
            return {
                'evidence_id': evidence.id,
                'evidence_type': 'original',
                'file_path': str(evidence_path),
                'file_name': filename,
                'frame_timestamp_ms': frame_timestamp_ms
            }
            
        except Exception as e:
            logger.error(f"Failed to store original threat image: {e}")
            return None

    async def _store_person_evidence(
        self,
        ticket_id: int,
        person_data: Dict,
        evidence_folder: Path
    ) -> Optional[Dict]:
        """Store person evidence."""
        try:
            person_id = person_data['person_identification']['person_id']
            frame_timestamp_ms = person_data['person_region']['frame_timestamp_ms']
            
            # Generate filename
            filename = f"person_{person_id}_{frame_timestamp_ms}ms.jpg"
            evidence_path = evidence_folder / filename
            
            # Copy person image
            if 'appearance_data' in person_data and person_data['appearance_data'].get('person_image_path'):
                source_path = Path(person_data['appearance_data']['person_image_path'])
                if source_path.exists():
                    shutil.copy2(source_path, evidence_path)
                else:
                    logger.warning(f"Person image not found: {source_path}")
                    return None
            else:
                logger.warning("No person image path in appearance data")
                return None
            
            # Create evidence record
            evidence = TicketEvidence(
                ticket_id=ticket_id,
                storage_file_id=0,  # Will be updated when file is registered
                evidence_type="person",
                file_path=str(evidence_path),
                file_name=filename,
                matched_face_id=person_data.get('face_analysis', {}).get('face_id'),
                match_confidence=person_data['person_identification']['confidence'],
                source_video_id=person_data.get('appearance_data', {}).get('video_id'),
                frame_timestamp_ms=frame_timestamp_ms,
                description=f"Person {person_id} - {person_data['person_identification']['identification_method']} identification"
            )
            
            self.session.add(evidence)
            await self.session.flush()
            
            return {
                'evidence_id': evidence.id,
                'evidence_type': 'person',
                'file_path': str(evidence_path),
                'file_name': filename,
                'person_id': person_id,
                'identification_method': person_data['person_identification']['identification_method'],
                'confidence': person_data['person_identification']['confidence']
            }
            
        except Exception as e:
            logger.error(f"Failed to store person evidence: {e}")
            return None

    async def _generate_threat_report(
        self,
        ticket_id: int,
        threat_assessment: Dict,
        person_analysis: Dict,
        related_persons: List[Dict]
    ) -> str:
        """Generate comprehensive threat report."""
        try:
            report_lines = []
            
            # Header
            report_lines.append("=" * 80)
            report_lines.append(f"THREAT DETECTION REPORT - TICKET #{ticket_id}")
            report_lines.append("=" * 80)
            report_lines.append("")
            
            # Threat Assessment
            report_lines.append("THREAT ASSESSMENT:")
            report_lines.append("-" * 40)
            report_lines.append(f"Threat Level: {threat_assessment.get('threat_level', 'UNKNOWN')}")
            report_lines.append(f"Confidence: {threat_assessment.get('threat_confidence', 0.0):.2f}")
            report_lines.append(f"Is Emergency: {threat_assessment.get('is_emergency', False)}")
            report_lines.append(f"Priority Level: {threat_assessment.get('priority_level', 0)}")
            report_lines.append("")
            
            # Threat Description
            report_lines.append("THREAT DESCRIPTION:")
            report_lines.append("-" * 40)
            report_lines.append(threat_assessment.get('threat_description', 'No description available'))
            report_lines.append("")
            
            # Threat Types
            threat_types = threat_assessment.get('threat_types', [])
            if threat_types:
                report_lines.append("THREAT TYPES:")
                report_lines.append("-" * 40)
                for threat_type in threat_types:
                    report_lines.append(f"• {threat_type}")
                report_lines.append("")
            
            # Recommended Action
            report_lines.append("RECOMMENDED ACTION:")
            report_lines.append("-" * 40)
            report_lines.append(threat_assessment.get('recommended_action', 'No specific action recommended'))
            report_lines.append("")
            
            # Person Analysis
            if person_analysis.get('persons'):
                report_lines.append("PERSONS DETECTED:")
                report_lines.append("-" * 40)
                
                for i, person_data in enumerate(person_analysis['persons'], 1):
                    person_id = person_data['person_identification']['person_id']
                    identification_method = person_data['person_identification']['identification_method']
                    confidence = person_data['person_identification']['confidence']
                    
                    report_lines.append(f"Person #{i}:")
                    report_lines.append(f"  ID: {person_id}")
                    report_lines.append(f"  Identification Method: {identification_method}")
                    report_lines.append(f"  Confidence: {confidence:.2f}")
                    
                    # Clothing information
                    clothing_analysis = person_data.get('clothing_analysis', {})
                    if clothing_analysis.get('clothing_signature'):
                        report_lines.append(f"  Clothing Signature: {clothing_analysis['clothing_signature']}")
                    
                    # Face information
                    face_analysis = person_data.get('face_analysis')
                    if face_analysis:
                        report_lines.append(f"  Face Detected: Yes")
                        if face_analysis.get('estimated_age'):
                            report_lines.append(f"  Estimated Age: {face_analysis['estimated_age']}")
                        if face_analysis.get('gender'):
                            report_lines.append(f"  Gender: {face_analysis['gender']}")
                        if face_analysis.get('ethnicity'):
                            report_lines.append(f"  Ethnicity: {face_analysis['ethnicity']}")
                    else:
                        report_lines.append(f"  Face Detected: No")
                    
                    report_lines.append("")
            
            # Related Persons
            if related_persons:
                report_lines.append("RELATED PERSONS FOUND:")
                report_lines.append("-" * 40)
                report_lines.append(f"Total related persons found: {len(related_persons)}")
                report_lines.append("")
                
                for i, person in enumerate(related_persons[:10], 1):  # Limit to 10
                    report_lines.append(f"Related Person #{i}:")
                    report_lines.append(f"  Person ID: {person['person_id']}")
                    report_lines.append(f"  Video ID: {person['video_id']}")
                    report_lines.append(f"  Timestamp: {person['frame_timestamp_ms']}ms")
                    report_lines.append(f"  Match Type: {person['match_type']}")
                    report_lines.append(f"  Match Confidence: {person['match_confidence']:.2f}")
                    report_lines.append(f"  Evidence File: {person['evidence_filename']}")
                    report_lines.append("")
                
                if len(related_persons) > 10:
                    report_lines.append(f"... and {len(related_persons) - 10} more related persons")
                    report_lines.append("")
            
            # Summary
            report_lines.append("SUMMARY:")
            report_lines.append("-" * 40)
            report_lines.append(f"Total persons detected: {person_analysis.get('person_count', 0)}")
            report_lines.append(f"Total related persons found: {len(related_persons)}")
            report_lines.append(f"Evidence files created: {len(related_persons) + person_analysis.get('person_count', 0) + 1}")
            report_lines.append("")
            
            # Footer
            report_lines.append("=" * 80)
            report_lines.append(f"Report generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            report_lines.append("=" * 80)
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"Failed to generate threat report: {e}")
            return f"Error generating threat report: {str(e)}"

    async def get_evidence_summary(self, ticket_id: int) -> Dict:
        """Get summary of evidence collected for a ticket."""
        try:
            # Get all evidence for ticket
            evidence_query = await self.session.execute(
                select(TicketEvidence).where(TicketEvidence.ticket_id == ticket_id)
            )
            evidence_list = evidence_query.scalars().all()
            
            # Categorize evidence
            evidence_by_type = {}
            for evidence in evidence_list:
                evidence_type = evidence.evidence_type
                if evidence_type not in evidence_by_type:
                    evidence_by_type[evidence_type] = []
                
                evidence_by_type[evidence_type].append({
                    'id': evidence.id,
                    'file_name': evidence.file_name,
                    'file_path': evidence.file_path,
                    'frame_timestamp_ms': evidence.frame_timestamp_ms,
                    'match_confidence': evidence.match_confidence,
                    'description': evidence.description
                })
            
            return {
                'ticket_id': ticket_id,
                'total_evidence_files': len(evidence_list),
                'evidence_by_type': evidence_by_type,
                'evidence_types': list(evidence_by_type.keys())
            }
            
        except Exception as e:
            logger.error(f"Failed to get evidence summary: {e}")
            return {
                'ticket_id': ticket_id,
                'total_evidence_files': 0,
                'evidence_by_type': {},
                'evidence_types': [],
                'error': str(e)
            }


# Import statement for datetime
from datetime import datetime
from sqlalchemy import select
