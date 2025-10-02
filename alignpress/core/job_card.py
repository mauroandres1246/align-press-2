"""
Job card management for tracking individual press jobs.

This module handles creation, updating, and persistence of job cards
that record each press operation including detection results.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict
import json
import logging

from .composition import Composition
from .schemas import LogoResultSchema

logger = logging.getLogger(__name__)


@dataclass
class JobCard:
    """
    Represents a single press job with detection results.

    Attributes:
        job_id: Unique job identifier (e.g., "JOB-20250928-001")
        timestamp_start: Job start time
        composition: Composition used for this job
        operator: Operator name/ID
        results: List of logo detection results
        timestamp_end: Job completion time (None if in progress)
        snapshot_path: Path to saved snapshot image
        notes: Additional notes or observations
    """

    job_id: str
    timestamp_start: datetime
    composition: Composition
    operator: str = "Unknown"
    results: List[LogoResultSchema] = field(default_factory=list)
    timestamp_end: Optional[datetime] = None
    snapshot_path: Optional[str] = None
    notes: str = ""

    @classmethod
    def create(
        cls,
        composition: Composition,
        operator: str = "Unknown",
        job_id: Optional[str] = None
    ) -> "JobCard":
        """
        Create a new job card.

        Args:
            composition: Composition for this job
            operator: Operator name/ID
            job_id: Optional custom job ID (auto-generated if not provided)

        Returns:
            New JobCard instance
        """
        if job_id is None:
            # Auto-generate job ID: JOB-YYYYMMDD-HHMMSS
            timestamp = datetime.now()
            job_id = timestamp.strftime("JOB-%Y%m%d-%H%M%S")

        logger.info(f"Creating job card: {job_id}")

        return cls(
            job_id=job_id,
            timestamp_start=datetime.now(),
            composition=composition,
            operator=operator
        )

    def add_results(self, results: List[LogoResultSchema]) -> None:
        """
        Add detection results to job card.

        Args:
            results: List of logo detection results
        """
        self.results = results
        logger.debug(f"Added {len(results)} results to job {self.job_id}")

    def finalize(self, snapshot_path: Optional[Path] = None, notes: str = "") -> None:
        """
        Finalize job and mark as complete.

        Args:
            snapshot_path: Optional path to saved snapshot
            notes: Additional notes
        """
        self.timestamp_end = datetime.now()
        if snapshot_path:
            self.snapshot_path = str(snapshot_path)
        if notes:
            self.notes = notes

        logger.info(f"Finalized job {self.job_id}")

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get job duration in seconds (None if not finalized)."""
        if self.timestamp_end is None:
            return None
        return (self.timestamp_end - self.timestamp_start).total_seconds()

    @property
    def is_successful(self) -> bool:
        """Check if all logos were detected successfully."""
        if not self.results:
            return False
        return all(result.found for result in self.results)

    @property
    def logos_found_count(self) -> int:
        """Count of logos successfully detected."""
        return sum(1 for result in self.results if result.found)

    @property
    def logos_total_count(self) -> int:
        """Total number of logos in job."""
        return len(self.results)

    @property
    def success_rate(self) -> float:
        """Success rate as percentage (0-100)."""
        if self.logos_total_count == 0:
            return 0.0
        return (self.logos_found_count / self.logos_total_count) * 100

    def get_summary(self) -> Dict[str, Any]:
        """
        Get human-readable job summary.

        Returns:
            Dictionary with job summary information
        """
        return {
            "job_id": self.job_id,
            "operator": self.operator,
            "platen": self.composition.platen.name,
            "style": self.composition.style.name,
            "variant": self.composition.variant.name if self.composition.variant else None,
            "logos_found": f"{self.logos_found_count}/{self.logos_total_count}",
            "success_rate": f"{self.success_rate:.1f}%",
            "duration": f"{self.duration_seconds:.1f}s" if self.duration_seconds else "In progress",
            "status": "SUCCESS" if self.is_successful else "PARTIAL" if self.logos_found_count > 0 else "FAILED"
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert job card to dictionary for serialization.

        Returns:
            Dictionary representation of job card
        """
        return {
            "job_id": self.job_id,
            "timestamp_start": self.timestamp_start.isoformat(),
            "timestamp_end": self.timestamp_end.isoformat() if self.timestamp_end else None,
            "duration_seconds": self.duration_seconds,
            "operator": self.operator,
            "composition": self.composition.to_dict(),
            "results": [result.model_dump() for result in self.results],
            "snapshot_path": self.snapshot_path,
            "notes": self.notes,
            "summary": {
                "logos_found": self.logos_found_count,
                "logos_total": self.logos_total_count,
                "success_rate": self.success_rate,
                "successful": self.is_successful
            }
        }

    def to_json(self, indent: int = 2) -> str:
        """
        Serialize job card to JSON string.

        Args:
            indent: JSON indentation level

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save(self, output_dir: Path = Path("logs/job_cards")) -> Path:
        """
        Save job card to disk as JSON file.

        Args:
            output_dir: Directory to save job cards

        Returns:
            Path to saved file

        Raises:
            IOError: If save fails
        """
        # Create output directory if needed
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        filename = f"{self.job_id}.json"
        output_path = output_dir / filename

        # Save to file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(self.to_json())

            logger.info(f"Saved job card: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to save job card: {e}")
            raise IOError(f"Failed to save job card: {e}") from e

    @classmethod
    def load(cls, path: Path) -> "JobCard":
        """
        Load job card from JSON file.

        Args:
            path: Path to job card JSON file

        Returns:
            Loaded JobCard instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is invalid
        """
        if not path.exists():
            raise FileNotFoundError(f"Job card not found: {path}")

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Note: This is simplified - full implementation would
            # need to reconstruct Composition and LogoResultSchema objects
            logger.info(f"Loaded job card: {data.get('job_id')}")
            return data  # Return dict for now

        except Exception as e:
            logger.error(f"Failed to load job card: {e}")
            raise ValueError(f"Invalid job card file: {e}") from e

    def __repr__(self) -> str:
        status = "✓" if self.is_successful else "✗"
        return (
            f"<JobCard {self.job_id}: {status} "
            f"{self.logos_found_count}/{self.logos_total_count} logos>"
        )
