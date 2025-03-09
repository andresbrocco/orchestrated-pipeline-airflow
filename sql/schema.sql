-- Weather Data Schema
-- Creates tables for storing weather observations and forecasts

-- Drop tables in reverse dependency order for idempotency
DROP TABLE IF EXISTS weather_forecasts;
DROP TABLE IF EXISTS weather_observations;
DROP TABLE IF EXISTS locations;

-- Locations table: cities being tracked
CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    city_name VARCHAR(100) NOT NULL,
    country_code VARCHAR(2) NOT NULL,
    latitude NUMERIC(9, 6) NOT NULL,
    longitude NUMERIC(9, 6) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (city_name, country_code)
);

-- Weather observations: current weather data from API
CREATE TABLE weather_observations (
    id SERIAL PRIMARY KEY,
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    observation_time TIMESTAMP WITH TIME ZONE NOT NULL,
    temperature NUMERIC(5, 2),
    feels_like NUMERIC(5, 2),
    humidity INTEGER,
    pressure INTEGER,
    wind_speed NUMERIC(5, 2),
    wind_direction INTEGER,
    weather_condition VARCHAR(50),
    weather_description VARCHAR(200),
    cloudiness INTEGER,
    visibility INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (location_id, observation_time)
);

-- Weather forecasts: predicted weather data
CREATE TABLE weather_forecasts (
    id SERIAL PRIMARY KEY,
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    forecast_time TIMESTAMP WITH TIME ZONE NOT NULL,
    predicted_for TIMESTAMP WITH TIME ZONE NOT NULL,
    temperature NUMERIC(5, 2),
    feels_like NUMERIC(5, 2),
    humidity INTEGER,
    pressure INTEGER,
    wind_speed NUMERIC(5, 2),
    wind_direction INTEGER,
    weather_condition VARCHAR(50),
    weather_description VARCHAR(200),
    cloudiness INTEGER,
    visibility INTEGER,
    precipitation_probability INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (location_id, forecast_time, predicted_for)
);

-- Indexes for common query patterns
CREATE INDEX idx_observations_time ON weather_observations(observation_time);
CREATE INDEX idx_observations_location ON weather_observations(location_id);
CREATE INDEX idx_forecasts_predicted_for ON weather_forecasts(predicted_for);
CREATE INDEX idx_forecasts_location ON weather_forecasts(location_id);
