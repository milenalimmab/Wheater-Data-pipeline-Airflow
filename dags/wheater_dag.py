"""
Pipeline DAG Wheather 
Extrai dados climáticos do OpenWheater API e armazena na AWS S3. 

Autora: Milena
Inspirado em: 
2025-10-14
"""


from airflow import DAG
from datetime import timedelta, datetime
from airflow.providers.http.sensors.http import HttpSensor
from airflow.providers.http.operators.http import HttpOperator
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.amazon.aws.transfers.local_to_s3 import LocalFilesystemToS3Operator
from airflow.models import Variable
from airflow.exceptions import AirflowException
import json
import pandas as pd
import boto3
import logging
import os

# ===========================================================================================
# CONSTANTES
# ===========================================================================================
DEFAULT_CITY = Variable.get("default_city")
logger = logging.getLogger(__name__)

 
# ===========================================================================================
# FUNÇÕES AUXILIARES
# ===========================================================================================

def kelvin_to_celsius(temp_in_kelvin: float) -> float:
    """
    Converte a temperatura de Kelvin para Celsius.
    
    Args:
        temp_in_kelvin: Temperatura em Kelvin
        
    Retorna:
        Temperatura em Celsius arredondada em 2 casas decimais
    """
    temp_in_celsius = temp_in_kelvin - 273.15
    return round(temp_in_celsius, 2) 

def transform_loaded_data(task_instance):
    """
    Transforma weather data num formato estruturado e salva como .csv 
    
    Args:
        task_instance: Airflow task instance para acesso XCom 
        
    Retorna:
        Caminho do arquivo .csv salvo
        
    Acusa:
        AirflowException: Se a extração ou transformação dos arquivos falhar
    """
    tmp_dir = "/tmp/weather_dag"
    os.makedirs(tmp_dir, exist_ok=True)
    try:
        # Obtém os dados da task anterior com XCom
        data = task_instance.xcom_pull(task_ids='extract_weather_data')
        
        if not data:
            raise AirflowException("Nenhum dado foi extraído da task extract_weather_data")

        # Extrai e transforma os dados
        city = data["name"]
        weather_description = data["weather"][0]['description']
        temp_celsius = kelvin_to_celsius(data["main"]["temp"])
        feels_like_celsius = kelvin_to_celsius(data["main"]["feels_like"])
        min_temp_celsius = kelvin_to_celsius(data["main"]["temp_min"])
        max_temp_celsius = kelvin_to_celsius(data["main"]["temp_max"])
        pressure = data["main"]["pressure"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]
        time_of_record  = datetime.utcfromtimestamp(data['dt'] + data['timezone'])
        sunrise_time = datetime.utcfromtimestamp(data['sys']['sunrise'] + data['timezone'])
        sunset_time = datetime.utcfromtimestamp(data['sys']['sunset'] + data['timezone'])

        # Estrutura os dados transformados 
        transformed_data = {"City": city,
                            "Description": weather_description,
                            "Temperature (C)": temp_celsius,
                            "Feels Like (C)": feels_like_celsius,
                            "Minimun Temp (C)": min_temp_celsius,
                            "Maximum Temp (C)": max_temp_celsius,
                            "Pressure": pressure,
                            "Humidity": humidity,
                            "Wind Speed": wind_speed,
                            "Time of Record": time_of_record,
                            "Sunrise (Local Time)": sunrise_time,
                            "Sunset (Local Time)": sunset_time
                            }
        
        # Cria Dataframe e salva em .csv
        df_data = pd.DataFrame([transformed_data])

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") 
        filename = f'weather_data_{city}_{timestamp}.csv'
        filepath = f'{tmp_dir}/{filename}'

        df_data.to_csv(filepath, index=False)
        logger.info(f"Weather data saved to {filepath}")
    
        return filepath

    except KeyError as e:
        raise AirflowException(f"Missing expected key in weather data: {e}")
    except Exception as e:
        raise AirflowException(f"Error transforming weather data: {e}")

def upload_to_s3(task_instance) -> None:
    """
    Faz o upload do arquivo .csv para AWS S3 bucket.
    
    Args:
        task_instance: Airflow task instance para acesso XCom
        
    Acusa:
        AirflowException: Se o upload falhar 
    """
    try:
        # Obtém o caminho do arquivo da task anterior
        filepath = task_instance.xcom_pull(task_ids='transform_loaded_weather_data')

        if not filepath:
            raise AirflowException("Nenhum caminho recebido para os dados") 
        
        # Obtém o nome do arquivo da task anterior
        filename = os.path.basename(filepath)

        if not filename:
            raise AirflowException("Nenhum nome recebido para os dados") 
        
        # Obtém as credenciais AWS das variáveis Airflow 
        aws_access_key = Variable.get("aws_access_key_id")
        aws_secret_key = Variable.get("aws_secret_access_key")
        bucket_name = Variable.get("s3_bucket_name")
        aws_region = Variable.get("aws_region", default_var="sa-east-1")

        # Cria cliente S3 
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
        
        # Upload para S3
        s3_key = f'weather-data/{filename}'
        s3_client.upload_file(filepath, bucket_name, s3_key)
        
        logger.info(f"File {filename} uploaded to s3://{bucket_name}/{s3_key}")
    
    except Exception as e:
        raise AirflowException(f"Error uploading to S3: {e}")


# ===========================================================================================
# CONFIGURAÇÃO DAG
# ===========================================================================================

default_args ={
    'owner': "airflow",
    'depends_on_past': False,
    'start_date': datetime(2025, 10, 10),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=2)
}

# ===========================================================================================
# DAG
# ===========================================================================================

with DAG(
    'weather_dag',
    default_args=default_args,
    description= 'Extrai dados climáticos do OpenWeather API e carrega para AWS S3',
    schedule= '@daily',
    catchup=False,
    params={'city': DEFAULT_CITY}
) as dag:

    #Task 0: obtém longitude e latidude pelo Geocoding API 

    get_city_coordinates = HttpOperator(
        task_id = 'get_city_coordinates',
        http_conn_id= 'weathermap_api',
        endpoint ='/geo/1.0/direct?q={{ params.city }}&limit=1&appid={{ var.value.openweather_api_key }}',
        method = 'GET',
        response_filter=lambda r: json.loads(r.text)[0], 
        log_response=True,
        doc_md= """ 
        ### Get City Coordinates
        Obtém as coordenadas (latitute e longitude) da cidade escolhida (DEFAULT_CITY) utilizando OpenWeather Geocoding API

        **Parameters**:
        - 'lat': Latitude (da task anterior)
        - 'lon': Longitude (da task anterior)
        - 'appid': API authentication key
        """
        )

    #Task 1: verifica se o api está respondendo
    is_weather_api_ready = HttpSensor(
        task_id = 'is_weather_api_ready',
        http_conn_id='weathermap_api',
        endpoint="/data/2.5/weather?lat={{ task_instance.xcom_pull(task_ids='get_city_coordinates')['lat'] }}&lon={{ task_instance.xcom_pull(task_ids='get_city_coordinates')['lon'] }}&appid={{ var.value.openweather_api_key }}",
        poke_interval=30,
        timeout=300,
        doc_md= """
        ## Wheater API Status
        Testa se o API está respondendo antes de fazer a extração dos dados
        """
        )

    #Task 2: extrai os dados do api
    extract_weather_data = HttpOperator(
        task_id= 'extract_weather_data',
        http_conn_id = 'weathermap_api',
        endpoint = "/data/2.5/weather?lat={{ task_instance.xcom_pull(task_ids='get_city_coordinates')['lat'] }}&lon={{ task_instance.xcom_pull(task_ids='get_city_coordinates')['lon'] }}&appid={{ var.value.openweather_api_key }}",
        method = 'GET',
        response_filter = lambda r: json.loads(r.text),
        log_response=True,
        doc_md="""
        ### Extract Wheater Data
        Faz a extração dos dados do API para as coordenadas especificadas.
        """
        )

    #Task 3: faz a transformação dos dados chamando uma função para isso
    transform_loaded_weather_data = PythonOperator(
        task_id='transform_loaded_weather_data',
        python_callable = transform_loaded_data,
        doc_md="""
        ### Transform Loaded Weather Data
        - Converte a temperatura de Kelvin para Celsius
        - Formata as informações de data e hora
        - Estrutura os dados em um DataFrame
        - Salva como um arquivo .csv
        """ 
        )

    #Task 4: faz upload do arquivo para S3
    upload_to_s3 = PythonOperator(
        task_id='upload_to_s3',
        python_callable=upload_to_s3,
        doc_md=""""
        ### Upload to S3
        Faz o upload dos dados .csv transformados para um AWS S3 Bucket. 
        """
       
    )
    
    #Define a ordem em que as taks são executadas
    get_city_coordinates >> is_weather_api_ready >> extract_weather_data >> transform_loaded_weather_data >> upload_to_s3