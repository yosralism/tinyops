from __future__ import annotations

import ipaddress
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.import_history import DeviceImportHistory

logger = logging.getLogger(__name__)

# Area mapping rules
AREA_MAPPING = {
    "West Java": ["BANDUNG", "CIREBON", "JAKARTA", "PURWAKARTA", "SUKABUMI", "SURAKARTA", "TASIKMALAYA"],
    "Central Java": ["PURWOKERTO", "SEMARANG", "TEGAL", "YOGYAKARTA"],
    "": ["UNKNOWN"]
}


@dataclass
class ChangeLog:
    """Record of a single field change."""
    mgmt_ip: str
    hostname: str
    field_changes: dict[str, tuple[any, any]]  # field: (old_value, new_value)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ErrorDetail:
    """Record of an import error."""
    row_number: int
    hostname: str | None
    mgmt_ip: str | None
    error: str


@dataclass
class ImportResult:
    """Summary of import operation."""
    total_rows: int
    inserted: int
    updated: int
    skipped: int
    errors: int
    changes_log: list[ChangeLog] = field(default_factory=list)
    error_details: list[ErrorDetail] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_rows == 0:
            return 0.0
        return ((self.inserted + self.updated) / self.total_rows) * 100


class DeviceImportService:
    """Service for importing/syncing devices from Excel files.
    
    Treats Excel as source of truth. Handles:
    - Duplicate detection by mgmt_ip
    - Field comparison and updates
    - Area mapping from city
    - Validation and error handling
    """
    
    # Expected Excel columns
    REQUIRED_COLUMNS = ["Hostname", "Loopback0"]
    EXCEL_COLUMN_MAPPING = {
        "Hostname": "hostname",
        "Loopback0": "mgmt_ip",
        "Site ID": "site_id",
        "Functional": "role",
        "City": "area",  # Will be mapped via rules
        "Software Version": "software_version",
        "Device Type": "platform",
    }
    
    def __init__(self, db: AsyncSession):
        """Initialize import service with database session."""
        self.db = db
    
    def _map_city_to_area(self, city: str | None) -> str:
        """Map city name to area using predefined rules.
        
        Args:
            city: City name from Excel (e.g., "BANDUNG", "SEMARANG")
            
        Returns:
            Area name (e.g., "West Java", "Central Java") or empty string if not mapped
        """
        if not city:
            return ""
        
        city_upper = city.strip().upper()
        for area, cities in AREA_MAPPING.items():
            if city_upper in cities:
                return area
        
        logger.warning(f"City '{city}' not found in area mapping")
        return ""
    
    def _validate_ip(self, ip_str: str) -> bool:
        """Validate IP address format.
        
        Args:
            ip_str: IP address string
            
        Returns:
            True if valid IPv4 address
        """
        try:
            ipaddress.IPv4Address(ip_str)
            return True
        except (ipaddress.AddressValueError, ValueError):
            return False
    
    def _validate_hostname(self, hostname: str) -> bool:
        """Validate hostname format.
        
        Args:
            hostname: Hostname string
            
        Returns:
            True if valid format (alphanumeric, hyphens, dots, no spaces)
        """
        if not hostname or " " in hostname:
            return False
        # Allow alphanumeric, hyphens, underscores, and dots (for FQDNs)
        return all(c.isalnum() or c in "-_." for c in hostname)
    
    def _read_excel(self, file_path: str | Path) -> pd.DataFrame:
        """Read Excel file and perform initial validation.
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            DataFrame with Excel data
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If required columns are missing
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")
        
        logger.info(f"Reading Excel file: {file_path}")
        df = pd.read_excel(file_path)
        
        # Check for required columns
        missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")
        
        logger.info(f"Excel loaded: {len(df)} rows, columns: {list(df.columns)}")
        return df
    
    def _transform_row(self, row: pd.Series, row_num: int) -> dict | None:
        """Transform Excel row to device data dictionary.
        
        Args:
            row: DataFrame row
            row_num: Row number (for error reporting)
            
        Returns:
            Device data dict or None if validation fails
        """
        # Extract and map fields
        device_data = {}
        
        for excel_col, model_field in self.EXCEL_COLUMN_MAPPING.items():
            if excel_col in row.index:
                value = row[excel_col]
                # Handle NaN values
                if pd.isna(value):
                    device_data[model_field] = None
                else:
                    device_data[model_field] = str(value).strip() if value else None
        
        # Apply area mapping
        if "area" in device_data and device_data["area"]:
            device_data["area"] = self._map_city_to_area(device_data["area"])
        
        # Set vendor (constant for all)
        device_data["vendor"] = "CISCO"
        
        # Region is TBD - set to None for now
        device_data["region"] = None
        
        return device_data
    
    def _validate_device_data(self, device_data: dict) -> tuple[bool, str | None]:
        """Validate device data.
        
        Args:
            device_data: Device data dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        if not device_data.get("hostname"):
            return False, "Missing hostname"
        
        if not device_data.get("mgmt_ip"):
            return False, "Missing mgmt_ip (Loopback0)"
        
        # Validate IP format
        if not self._validate_ip(device_data["mgmt_ip"]):
            return False, f"Invalid IP address: {device_data['mgmt_ip']}"
        
        # Validate hostname format
        if not self._validate_hostname(device_data["hostname"]):
            return False, f"Invalid hostname format: {device_data['hostname']}"
        
        return True, None
    
    async def _find_existing_device(self, mgmt_ip: str) -> Device | None:
        """Find existing device by mgmt_ip.
        
        Args:
            mgmt_ip: Management IP address
            
        Returns:
            Device if found, None otherwise
        """
        stmt = select(Device).where(Device.mgmt_ip == mgmt_ip)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    def _detect_changes(self, existing: Device, new_data: dict) -> dict[str, tuple[any, any]]:
        """Detect field changes between existing device and new data.
        
        Args:
            existing: Existing Device model
            new_data: New device data from Excel
            
        Returns:
            Dictionary of field_name: (old_value, new_value) for changed fields
        """
        changes = {}
        
        for field, new_value in new_data.items():
            if field in ["created_at", "updated_at", "id"]:
                continue
            
            old_value = getattr(existing, field, None)
            
            # Normalize values for comparison (handle None, empty strings)
            old_normalized = old_value if old_value else None
            new_normalized = new_value if new_value else None
            
            if old_normalized != new_normalized:
                changes[field] = (old_value, new_value)
        
        return changes
    
    async def import_from_excel(
        self,
        file_path: str | Path,
        dry_run: bool = False,
        performed_by: str | None = None,
    ) -> ImportResult:
        """Import devices from Excel file.
        
        Args:
            file_path: Path to Excel file
            dry_run: If True, don't commit changes to database
            performed_by: Username of person performing import
            
        Returns:
            ImportResult with statistics and details
        """
        file_path = Path(file_path)
        filename = file_path.name
        
        logger.info(f"Starting device import from {filename} (dry_run={dry_run})")
        
        # Read Excel
        try:
            df = self._read_excel(file_path)
        except Exception as e:
            logger.error(f"Failed to read Excel: {e}")
            raise
        
        # Initialize result tracking
        result = ImportResult(
            total_rows=len(df),
            inserted=0,
            updated=0,
            skipped=0,
            errors=0,
        )
        
        # Process each row
        for idx, row in df.iterrows():
            row_num = idx + 2  # Excel row number (header is row 1)
            
            try:
                # Transform row
                device_data = self._transform_row(row, row_num)
                if device_data is None:
                    result.skipped += 1
                    continue
                
                # Validate
                is_valid, error_msg = self._validate_device_data(device_data)
                if not is_valid:
                    result.errors += 1
                    result.error_details.append(ErrorDetail(
                        row_number=row_num,
                        hostname=device_data.get("hostname"),
                        mgmt_ip=device_data.get("mgmt_ip"),
                        error=error_msg or "Validation failed"
                    ))
                    logger.warning(f"Row {row_num} validation failed: {error_msg}")
                    continue
                
                # Check if device exists
                existing = await self._find_existing_device(device_data["mgmt_ip"])
                
                if existing:
                    # Update existing device
                    changes = self._detect_changes(existing, device_data)
                    
                    if changes:
                        if not dry_run:
                            for field, (old_val, new_val) in changes.items():
                                setattr(existing, field, new_val)
                        
                        result.updated += 1
                        result.changes_log.append(ChangeLog(
                            mgmt_ip=device_data["mgmt_ip"],
                            hostname=device_data["hostname"],
                            field_changes=changes
                        ))
                        logger.info(f"Updated device {device_data['hostname']} ({device_data['mgmt_ip']}): {len(changes)} changes")
                    else:
                        result.skipped += 1
                        logger.debug(f"Skipped device {device_data['hostname']}: no changes")
                else:
                    # Insert new device
                    if not dry_run:
                        new_device = Device(**device_data)
                        self.db.add(new_device)
                    
                    result.inserted += 1
                    logger.info(f"Inserted new device {device_data['hostname']} ({device_data['mgmt_ip']})")
            
            except Exception as e:
                result.errors += 1
                result.error_details.append(ErrorDetail(
                    row_number=row_num,
                    hostname=None,
                    mgmt_ip=None,
                    error=str(e)
                ))
                logger.error(f"Error processing row {row_num}: {e}", exc_info=True)
        
        # Commit changes
        if not dry_run:
            try:
                await self.db.commit()
                logger.info("Changes committed to database")
                
                # Record import history
                history = DeviceImportHistory(
                    filename=filename,
                    total_rows=result.total_rows,
                    inserted=result.inserted,
                    updated=result.updated,
                    skipped=result.skipped,
                    errors=result.errors,
                    changes_summary={
                        "success_rate": result.success_rate,
                        "changes_count": len(result.changes_log),
                    },
                    performed_by=performed_by,
                )
                self.db.add(history)
                await self.db.commit()
                logger.info("Import history recorded")
            except Exception as e:
                await self.db.rollback()
                logger.error(f"Failed to commit changes: {e}", exc_info=True)
                raise
        else:
            logger.info("Dry run completed - no changes committed")
        
        logger.info(
            f"Import complete: {result.inserted} inserted, {result.updated} updated, "
            f"{result.skipped} skipped, {result.errors} errors"
        )
        
        return result
