"""Tests for anomaly detection module."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from dags.tasks.anomaly import (
    detect_temperature_anomalies,
    detect_missing_locations,
    detect_outliers,
    check_anomalies,
)


@patch('dags.tasks.anomaly.PostgresHook')
def test_detect_temperature_anomalies(mock_hook):
    """Test temperature spike detection."""
    mock_instance = MagicMock()
    mock_hook.return_value = mock_instance

    mock_instance.get_records.return_value = [
        ('São Paulo', 'BR', datetime.now(), 25.0, 10.0, 15.0),
        ('Campinas', 'BR', datetime.now(), 30.0, 15.0, 15.0),
    ]

    anomalies = detect_temperature_anomalies()

    assert len(anomalies) == 2
    assert anomalies[0]['type'] == 'temperature_spike'
    assert anomalies[0]['location'] == 'São Paulo, BR'
    assert anomalies[0]['change'] == 15.0


@patch('dags.tasks.anomaly.PostgresHook')
def test_detect_missing_locations(mock_hook):
    """Test missing/stale data detection."""
    mock_instance = MagicMock()
    mock_hook.return_value = mock_instance

    old_time = datetime.now() - timedelta(hours=5)
    mock_instance.get_records.return_value = [
        (1, 'Guarapari', 'BR', old_time),
        (2, 'Ubatuba', 'BR', None),
    ]

    anomalies = detect_missing_locations()

    assert len(anomalies) == 2
    assert anomalies[0]['type'] == 'missing_data'
    assert anomalies[1]['last_observation'] is None


@patch('dags.tasks.anomaly.PostgresHook')
def test_detect_outliers(mock_hook):
    """Test outlier detection."""
    mock_instance = MagicMock()
    mock_hook.return_value = mock_instance

    mock_instance.get_records.return_value = [
        ('São Paulo', 'BR', datetime.now(), 150.0, 150, 200.0),
    ]

    anomalies = detect_outliers()

    assert len(anomalies) == 1
    assert anomalies[0]['type'] == 'outlier'
    assert len(anomalies[0]['issues']) == 3


@patch('dags.tasks.anomaly.detect_temperature_anomalies')
@patch('dags.tasks.anomaly.detect_missing_locations')
@patch('dags.tasks.anomaly.detect_outliers')
@patch('dags.tasks.anomaly.store_anomaly')
def test_check_anomalies(mock_store, mock_outliers, mock_missing, mock_temp):
    """Test main anomaly check function."""
    mock_temp.return_value = [{'type': 'temperature_spike'}]
    mock_missing.return_value = []
    mock_outliers.return_value = [{'type': 'outlier'}]

    context = {'ti': MagicMock()}

    result = check_anomalies(**context)

    assert len(result['temperature_spikes']) == 1
    assert len(result['missing_data']) == 0
    assert len(result['outliers']) == 1
    assert mock_store.call_count == 2
