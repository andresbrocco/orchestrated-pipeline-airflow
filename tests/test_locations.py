"""Unit tests for location management functions."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from tasks.locations import (
    load_locations_from_config,
    get_locations_from_db,
    get_location_by_id,
    get_location_by_city,
    get_api_params
)


class TestLoadLocationsFromConfig:
    """Tests for load_locations_from_config function."""

    def test_load_valid_config(self, sample_locations_config):
        """Test loading locations from valid config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_locations_config, f)
            temp_path = Path(f.name)

        with patch('tasks.locations.CONFIG_PATH', temp_path):
            result = load_locations_from_config()

        assert len(result) == 2
        assert result[0]['city'] == 'São Paulo'
        assert result[1]['city'] == 'Rio de Janeiro'

        temp_path.unlink()

    def test_load_nonexistent_config(self):
        """Test handling of missing config file."""
        with patch('tasks.locations.CONFIG_PATH', Path('/nonexistent/path.json')):
            result = load_locations_from_config()

        assert result == []

    def test_load_empty_config(self):
        """Test loading empty locations list."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([], f)
            temp_path = Path(f.name)

        with patch('tasks.locations.CONFIG_PATH', temp_path):
            result = load_locations_from_config()

        assert result == []

        temp_path.unlink()


class TestGetLocationsFromDb:
    """Tests for get_locations_from_db function."""

    @patch('tasks.locations.PostgresHook')
    def test_get_all_locations(self, mock_hook_class):
        """Test retrieving all locations from database."""
        mock_hook = MagicMock()
        mock_hook.get_records.return_value = [
            (1, 'São Paulo', 'BR', -23.5505, -46.6333),
            (2, 'Rio de Janeiro', 'BR', -22.9068, -43.1729)
        ]
        mock_hook_class.return_value = mock_hook

        result = get_locations_from_db()

        assert len(result) == 2
        assert result[0]['id'] == 1
        assert result[0]['city'] == 'São Paulo'
        assert result[0]['country'] == 'BR'
        assert result[0]['lat'] == -23.5505
        assert result[0]['lon'] == -46.6333
        assert result[1]['city'] == 'Rio de Janeiro'

        mock_hook_class.assert_called_once_with(postgres_conn_id='weather_postgres')

    @patch('tasks.locations.PostgresHook')
    def test_get_locations_empty_db(self, mock_hook_class):
        """Test handling of empty database."""
        mock_hook = MagicMock()
        mock_hook.get_records.return_value = []
        mock_hook_class.return_value = mock_hook

        result = get_locations_from_db()

        assert result == []


class TestGetLocationById:
    """Tests for get_location_by_id function."""

    @patch('tasks.locations.PostgresHook')
    def test_get_existing_location(self, mock_hook_class):
        """Test retrieving location by valid ID."""
        mock_hook = MagicMock()
        mock_hook.get_first.return_value = (1, 'São Paulo', 'BR', -23.5505, -46.6333)
        mock_hook_class.return_value = mock_hook

        result = get_location_by_id(1)

        assert result is not None
        assert result['id'] == 1
        assert result['city'] == 'São Paulo'
        assert result['lat'] == -23.5505

    @patch('tasks.locations.PostgresHook')
    def test_get_nonexistent_location(self, mock_hook_class):
        """Test handling of nonexistent location ID."""
        mock_hook = MagicMock()
        mock_hook.get_first.return_value = None
        mock_hook_class.return_value = mock_hook

        result = get_location_by_id(999)

        assert result is None

    @patch('tasks.locations.PostgresHook')
    def test_coordinates_are_floats(self, mock_hook_class):
        """Test that coordinates are converted to floats."""
        mock_hook = MagicMock()
        # Simulate Decimal return from PostgreSQL
        from decimal import Decimal
        mock_hook.get_first.return_value = (
            1, 'São Paulo', 'BR',
            Decimal('-23.5505'), Decimal('-46.6333')
        )
        mock_hook_class.return_value = mock_hook

        result = get_location_by_id(1)

        assert isinstance(result['lat'], float)
        assert isinstance(result['lon'], float)


class TestGetLocationByCity:
    """Tests for get_location_by_city function."""

    @patch('tasks.locations.PostgresHook')
    def test_get_by_city_name_only(self, mock_hook_class):
        """Test retrieving location by city name only."""
        mock_hook = MagicMock()
        mock_hook.get_first.return_value = (1, 'São Paulo', 'BR', -23.5505, -46.6333)
        mock_hook_class.return_value = mock_hook

        result = get_location_by_city('São Paulo')

        assert result is not None
        assert result['city'] == 'São Paulo'

        # Verify SQL query uses only city name
        call_args = mock_hook.get_first.call_args
        assert 'city_name = %s' in call_args[0][0]
        assert call_args[1]['parameters'] == ('São Paulo',)

    @patch('tasks.locations.PostgresHook')
    def test_get_by_city_and_country(self, mock_hook_class):
        """Test retrieving location by city and country."""
        mock_hook = MagicMock()
        mock_hook.get_first.return_value = (1, 'São Paulo', 'BR', -23.5505, -46.6333)
        mock_hook_class.return_value = mock_hook

        result = get_location_by_city('São Paulo', 'BR')

        assert result is not None

        # Verify SQL query uses both city and country
        call_args = mock_hook.get_first.call_args
        assert 'city_name = %s AND country_code = %s' in call_args[0][0]
        assert call_args[1]['parameters'] == ('São Paulo', 'BR')

    @patch('tasks.locations.PostgresHook')
    def test_city_not_found(self, mock_hook_class):
        """Test handling of nonexistent city."""
        mock_hook = MagicMock()
        mock_hook.get_first.return_value = None
        mock_hook_class.return_value = mock_hook

        result = get_location_by_city('Unknown City')

        assert result is None


class TestGetApiParams:
    """Tests for get_api_params function."""

    def test_extract_coordinates(self, sample_location):
        """Test extracting API parameters from location."""
        result = get_api_params(sample_location)

        assert result == {'lat': -23.5505, 'lon': -46.6333}

    def test_only_coordinates_returned(self, sample_location):
        """Test that only lat/lon are returned."""
        result = get_api_params(sample_location)

        assert set(result.keys()) == {'lat', 'lon'}
        assert 'city' not in result
        assert 'id' not in result

    def test_minimal_location(self):
        """Test with minimal location data."""
        location = {'lat': 0.0, 'lon': 0.0}
        result = get_api_params(location)

        assert result == {'lat': 0.0, 'lon': 0.0}
