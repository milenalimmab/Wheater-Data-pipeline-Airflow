<<<<<<< HEAD
# 🌤️ Weather Data Pipeline with Apache Airflow

A data pipeline that automatically extracts weather data from OpenWeatherMap API, transforms it, and loads it into AWS S3 for further analysis.

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Data Schema](#data-schema)


## ✨ Features

- **Automated Geocoding**: Automatically fetches coordinates for any city using OpenWeatherMap Geocoding API
- **Data Transformation**: Converts temperatures from Kelvin to Celsius and formats timestamps
- **AWS S3 Integration**: Stores processed weather data in S3 buckets with organized structure
- **Highly Configurable**: Easy to configure via Airflow Variables and Parameters
- **Scheduled Execution**: Runs daily by default (customizable)
- **Clean Output**: Generates well-structured CSV files ready for analysis

## 🏗️ Architecture

```
┌─────────────────────────┐
│  Get City Coordinates   │  ← Geocoding API
│   (HttpOperator)        │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Check API Availability │  ← Health Check
│     (HttpSensor)        │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Extract Weather Data   │  ← Weather API
│     (HttpOperator)      │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Transform Data        │  ← Data Processing
│  (PythonOperator)       │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│    Upload to S3         │  ← AWS S3
│  (PythonOperator)       │
└─────────────────────────┘
```

## 🔧 Prerequisites

Ensure you have:

- **Python 3.8+** installed
- **Apache Airflow 2.7+** installed
- **AWS Account** with S3 access
- **OpenWeatherMap API key** ([Get one free here](https://openweathermap.org/api))
- **AWS credentials** (Access Key ID and Secret Access Key)

## ⚙️ Configuration

### Step 1: Configure HTTP Connection

1. Access Airflow UI
2. Go to **Admin → Connections**
3. Click **+** to add a new connection
4. Fill in:
   - **Connection Id**: `weathermap_api`
   - **Connection Type**: `HTTP`
   - **Host**: `https://api.openweathermap.org`
5. Click **Save**

### Step 2: Set Airflow Variables

Go to **Admin → Variables** and create the following variables:

| Key | Example Value | Description |
|-----|---------------|-------------|
| `openweather_api_key` | `your_api_key_here` | OpenWeatherMap API key |
| `aws_access_key_id` | `AKIAIOSFODNN7EXAMPLE` | AWS Access Key ID |
| `aws_secret_access_key` | `wJalrXUtnFEMI...` | AWS Secret Access Key |
| `s3_bucket_name` | `my-weather-data-bucket` | S3 bucket name |
| `aws_region` | `us-east-1` | AWS region (e.g., sa-east-1) |
| `default city` | `São Paulo` | Default city |

This increases security by not exposing your keys directly in the code and also makes it easier to change cities and regions.

### Run the DAG

**Via UI**
1. Go to `http://localhost:8080`
2. Find `weather_data_pipeline` DAG
3. Toggle it **ON**
4. Click **Trigger DAG** (play button)



## 📊 Data Schema

The pipeline generates CSV files with the following structure:

| Column | Type | Description |
|--------|------|-------------|
| City | string | City name |
| Description | string | Weather description (e.g., "clear sky") |
| Temperature (C) | float | Current temperature in Celsius |
| Feels Like (C) | float | Feels like temperature in Celsius |
| Minimum Temp (C) | float | Minimum temperature |
| Maximum Temp (C) | float | Maximum temperature |
| Pressure | int | Atmospheric pressure (hPa) |
| Humidity | int | Humidity percentage |
| Wind Speed | float | Wind speed (m/s) |
| Time of Record | datetime | Timestamp of the record |
| Sunrise (Local Time) | datetime | Sunrise time |
| Sunset (Local Time) | datetime | Sunset time |

You can also filter the data to include/exclude fields. 

**S3 Path Structure:**
```
s3://your-bucket-name/
└── weather-data/
    ├── weather_data_London_20251015_143000.csv
    ├── weather_data_Paris_20251015_143500.csv
    └── weather_data_Tokyo_20251015_144000.csv
```

 The filename follows the structure: weather_data_**Default_city** _ **Y%M%D** _ **h%m%s%**.csv


## 🙏 Acknowledgments

- [OpenWeatherMap API](https://openweathermap.org/api) - Weather data provider
- [Apache Airflow](https://airflow.apache.org/) - Workflow orchestration
- [AWS S3](https://aws.amazon.com/s3/) - Cloud storage
- [Pandas](https://pandas.pydata.org/) - Data manipulation

## 👤 Author

**Milena L.**

- GitHub: [@milenalimmab](https://github.com/milenalimmab)
- LinkedIn: [Milena Lima](https://www.linkedin.com/in/milenalimma/)


