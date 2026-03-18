from __future__ import annotations

import pytest
from app.services.device_import_service import DeviceImportService, AREA_MAPPING


class TestAreaMapping:
    """Test city to area mapping logic."""
    
    @pytest.fixture
    def service(self, db_session):
        return DeviceImportService(db_session)
    
    def test_map_west_java_cities(self, service):
        """Test West Java cities map correctly."""
        assert service._map_city_to_area("BANDUNG") == "West Java"
        assert service._map_city_to_area("JAKARTA") == "West Java"
        assert service._map_city_to_area("CIREBON") == "West Java"
        assert service._map_city_to_area("PURWAKARTA") == "West Java"
        assert service._map_city_to_area("SUKABUMI") == "West Java"
        assert service._map_city_to_area("SURAKARTA") == "West Java"
        assert service._map_city_to_area("TASIKMALAYA") == "West Java"
    
    def test_map_central_java_cities(self, service):
        """Test Central Java cities map correctly."""
        assert service._map_city_to_area("PURWOKERTO") == "Central Java"
        assert service._map_city_to_area("SEMARANG") == "Central Java"
        assert service._map_city_to_area("TEGAL") == "Central Java"
        assert service._map_city_to_area("YOGYAKARTA") == "Central Java"
    
    def test_map_case_insensitive(self, service):
        """Test mapping is case insensitive."""
        assert service._map_city_to_area("bandung") == "West Java"
        assert service._map_city_to_area("Bandung") == "West Java"
        assert service._map_city_to_area("SEMARANG") == "Central Java"
        assert service._map_city_to_area("semarang") == "Central Java"
    
    def test_map_with_whitespace(self, service):
        """Test mapping handles whitespace."""
        assert service._map_city_to_area("  BANDUNG  ") == "West Java"
        assert service._map_city_to_area(" SEMARANG ") == "Central Java"
    
    def test_map_unknown_city(self, service):
        """Test unknown city returns empty string."""
        assert service._map_city_to_area("UNKNOWN") == ""
        assert service._map_city_to_area("MALANG") == ""
        assert service._map_city_to_area("BALI") == ""
    
    def test_map_none_or_empty(self, service):
        """Test None or empty returns empty string."""
        assert service._map_city_to_area(None) == ""
        assert service._map_city_to_area("") == ""


class TestIPValidation:
    """Test IP address validation."""
    
    @pytest.fixture
    def service(self, db_session):
        return DeviceImportService(db_session)
    
    def test_valid_ipv4(self, service):
        """Test valid IPv4 addresses."""
        assert service._validate_ip("192.168.1.1") is True
        assert service._validate_ip("10.0.0.1") is True
        assert service._validate_ip("114.1.206.86") is True
        assert service._validate_ip("255.255.255.255") is True
    
    def test_invalid_ipv4(self, service):
        """Test invalid IPv4 addresses."""
        assert service._validate_ip("256.1.1.1") is False
        assert service._validate_ip("192.168.1") is False
        assert service._validate_ip("192.168.1.1.1") is False
        assert service._validate_ip("invalid") is False
        assert service._validate_ip("") is False


class TestHostnameValidation:
    """Test hostname validation."""
    
    @pytest.fixture
    def service(self, db_session):
        return DeviceImportService(db_session)
    
    def test_valid_hostnames(self, service):
        """Test valid hostname formats."""
        assert service._validate_hostname("router1") is True
        assert service._validate_hostname("SKA-GRPM-EN1-C516Z") is True
        assert service._validate_hostname("device_name") is True
        assert service._validate_hostname("device-name-123") is True
        assert service._validate_hostname("router.example.com") is True
    
    def test_invalid_hostnames(self, service):
        """Test invalid hostname formats."""
        assert service._validate_hostname("") is False
        assert service._validate_hostname("host name") is False  # Space
        assert service._validate_hostname(None) is False


class TestDeviceDataValidation:
    """Test device data validation."""
    
    @pytest.fixture
    def service(self, db_session):
        return DeviceImportService(db_session)
    
    def test_valid_device_data(self, service):
        """Test valid device data passes validation."""
        device_data = {
            "hostname": "router1",
            "mgmt_ip": "192.168.1.1",
            "vendor": "CISCO",
        }
        is_valid, error = service._validate_device_data(device_data)
        assert is_valid is True
        assert error is None
    
    def test_missing_hostname(self, service):
        """Test missing hostname fails validation."""
        device_data = {
            "mgmt_ip": "192.168.1.1",
        }
        is_valid, error = service._validate_device_data(device_data)
        assert is_valid is False
        assert "hostname" in error.lower()
    
    def test_missing_mgmt_ip(self, service):
        """Test missing mgmt_ip fails validation."""
        device_data = {
            "hostname": "router1",
        }
        is_valid, error = service._validate_device_data(device_data)
        assert is_valid is False
        assert "mgmt_ip" in error.lower()
    
    def test_invalid_ip_format(self, service):
        """Test invalid IP format fails validation."""
        device_data = {
            "hostname": "router1",
            "mgmt_ip": "invalid",
        }
        is_valid, error = service._validate_device_data(device_data)
        assert is_valid is False
        assert "invalid" in error.lower()
    
    def test_invalid_hostname_format(self, service):
        """Test invalid hostname format fails validation."""
        device_data = {
            "hostname": "host name",  # Space
            "mgmt_ip": "192.168.1.1",
        }
        is_valid, error = service._validate_device_data(device_data)
        assert is_valid is False
        assert "hostname" in error.lower()
