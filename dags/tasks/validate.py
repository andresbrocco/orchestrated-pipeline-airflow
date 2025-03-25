"""Data quality validation module."""

import logging

logger = logging.getLogger(__name__)


def check_data_quality(transformed_data):
    """Check if transformed data meets quality standards."""
    if not transformed_data:
        logger.warning("No data to validate")
        return False

    issues = []

    for item in transformed_data:
        location = item.get("city", "Unknown")
        data = item.get("transformed", {})

        observation = data.get("observation")
        if observation:
            temp = observation.get("temperature")
            if temp is None:
                issues.append(f"{location}: missing temperature")
            elif temp < -50 or temp > 60:
                issues.append(f"{location}: temperature out of range ({temp}°C)")

            humidity = observation.get("humidity")
            if humidity is not None and (humidity < 0 or humidity > 100):
                issues.append(f"{location}: invalid humidity ({humidity}%)")

        forecasts = data.get("forecasts", [])
        if not forecasts:
            issues.append(f"{location}: no forecast data")

    if issues:
        logger.warning(f"Data quality issues found: {len(issues)} problems")
        for issue in issues[:5]:
            logger.warning(f"  - {issue}")
        if len(issues) > 5:
            logger.warning(f"  ... and {len(issues) - 5} more")
        return False

    logger.info(f"Data quality check passed for {len(transformed_data)} locations")
    return True
