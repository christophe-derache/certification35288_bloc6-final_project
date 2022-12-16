
import uvicorn
import pandas as pd 
from pydantic import BaseModel, conlist
from typing import Literal, List, Union
from fastapi import FastAPI, File, UploadFile
from geopy.distance import great_circle as GRC
import joblib
import numpy as np
import json


from typing import List

description = """
Bienvenue dans notre simulateur intelligent de prix de l'immobilier pour la ville de Lyon !

## Machine Learning

C'est un endpoint de machine learning qui prédit le prix de l'immobilier. Voici le endpoint:

* `/predict` qui accepte un formulaire rempli sur le site https://immo-lyon-project.onrender.com

"""

tags_metadata = [
    
    {
        "name": "Machine_Learning",
        "description": "Prediction Endpoint."
    }
]

app = FastAPI(
    title="🏠 I(A)mmo-Lyon API",
    description=description,
    version="0.1",
    openapi_tags=tags_metadata
)


class FormFeatures(BaseModel):
    type_batiment : Literal["Appartement", "Maison"] = "Appartement"
    num_piece : int = 4
    surface : float = 100
    code_postal : int = 69002
    long : float = 4.877659 #already calculated in streamlit app (transparent for user)
    lat : float = 45.735974 #already calculated in streamlit app (transparent for user)
    diag : str = 'D'
    annee_construction : int = 2010


@app.get("/")
async def index():

    message = "Hello world! If you want to know how to use the API, check out documentation at `/docs`"

    return message

@app.post("/predict", tags=["Machine_Learning"])
async def predict(formFeatures: FormFeatures):
    """
    Prédiction du prix de l'immobilier en fonction du questionnaire rempli! 
    """
    #Building dataframe to make predictions with the model

    index_prix_appt = 4.5 #current value in December 2022 for flats (source INSEE)
    index_prix_maison = 8.5 #current value in December 2022 for houses (source INSEE)
    if formFeatures.type_batiment == 'Appartement' :
        index_prix_pred = index_prix_appt
    else :
        index_prix_pred = index_prix_maison
    
    # find arrondissement
    arrdt_int_pred = int(repr(formFeatures.code_postal)[-1])

    # convert diag dpe into string
    dict_dpe = {'A' : '6', 'B' : '5', 'C' : '4', 'D' : 3, 'E' : '2', 'F' : '1', 'G' : '0'}
    diag_dpe_int_pred = dict_dpe[f'{formFeatures.diag}']
    
    # find closest locations
    long_pred = formFeatures.long
    lat_pred = formFeatures.lat
    tuple_gps = (lat_pred, long_pred)

    df_interest = pd.read_csv('final_interest_dataframe_filtered.csv')

    list_gps = []

    for longitude, latitude in zip(df_interest.longitude, df_interest.latitude):
        list_gps.append((latitude, longitude))
    
    df_interest['tuple_gps'] = list_gps

    mask_school =   (df_interest['category']=='school')
    df_school = df_interest.loc[mask_school,:]

    mask_bakery =  (df_interest['category']=='bakery') 
    df_bakery = df_interest.loc[mask_bakery,:]

    mask_supermarket =  (df_interest['category']=='supermarket') 
    df_supermarket = df_interest.loc[mask_supermarket,:]

    mask_metro =  (df_interest['category']=='station_metro_A') | \
            (df_interest['category']=='station_metro_B') | \
            (df_interest['category']=='station_metro_C') | \
            (df_interest['category']=='station_metro_D') 
    df_metro = df_interest.loc[mask_metro,:]

    mask_tram =  (df_interest['category']=='arret_tram_T1') | \
            (df_interest['category']=='arret_tram_T2') | \
            (df_interest['category']=='arret_tram_T3') | \
            (df_interest['category']=='arret_tram_T4') | \
            (df_interest['category']=='arret_tram_T5') | \
            (df_interest['category']=='arret_tram_T6') 
    df_tram = df_interest.loc[mask_tram,:]

    def calculate_distances(point1, dataframe) :

        list_distances = []

        for i in dataframe.index.to_list() :
            point = dataframe.at[i,'tuple_gps']
            distance = round(GRC(point1,point).m,2)
            list_distances.append(distance)

        distance_min = min(list_distances)
        
        return distance_min

    list_data = [df_school, df_bakery, df_supermarket, df_metro, df_tram]
    result_distances = [calculate_distances(tuple_gps, item) for item in list_data]

    
    # Read data
    surface_pred = formFeatures.surface
    num_piece_pred = formFeatures.num_piece
    type_batiment_pred = formFeatures.type_batiment
    year_pred = 2022 #current value at app deployment
    closest_school_pred = result_distances[0]
    closest_bakery_pred = result_distances[1]
    closest_supermarket_pred = result_distances[2]
    closest_metro_pred = result_distances[3]
    closest_tram_pred = result_distances[4]
    diag_pred = formFeatures.diag
    annee_construction_pred = formFeatures.annee_construction

    features_list = ['surface_reelle_bati','longitude', 'latitude', 'nombre_pieces_principales', 'type_local', 'year', 'index_prix', 'closest_school_(m)', 'closest_bakery_(m)', 'closest_supermarket_(m)', 'closest_metro_(m)', 'closest_tram_(m)','diag_dpe_int', 'annee_construction_dpe', 'arrdt_int']
    features_values = [surface_pred, long_pred, lat_pred, num_piece_pred, type_batiment_pred, year_pred, index_prix_pred, closest_school_pred, closest_bakery_pred, closest_supermarket_pred, closest_metro_pred, closest_tram_pred, diag_dpe_int_pred, annee_construction_pred, arrdt_int_pred]
    X_topredict = pd.DataFrame(np.array([features_values]), columns = features_list)

    # Load model
    loaded_model = joblib.load('xgbregressor.joblib')
    
    #prediction with exp because the machine learning model is in log
    prediction = np.exp(loaded_model.predict(X_topredict))

    # Format response
    response = {"prediction": prediction.tolist()[0]}

    return response


if __name__=="__main__":
    uvicorn.run(app, host="0.0.0.0", port=4000)