import streamlit as st
import scipy
import requests
import pandas as pd
import plotly.express as px 
import plotly.graph_objects as go
import numpy as np
from geopy.geocoders import Nominatim
from geopy.distance import great_circle as GRC
import json
import re

MODEL_FINAL = 'https://app-immo-lyon.herokuapp.com/predict' # API to request to make predictions
END_NOMINATIM =  "https://nominatim.openstreetmap.org/" # to get the GPS coordinates of real estates
APPARTMENT = "Appartement"
HOUSE = "Maison"

df = pd.read_csv("immo_lyon17_22Epuré.csv", low_memory = False) # dataset with all the real estates sold in Lyon, in order to show several properties on the map

### Configuration
st.set_page_config(
    page_title="I(A)mmo-Lyon",
    page_icon="🦠 ",
    layout="wide"
)

### App
st.title('I(A)mmo-Lyon')
st.markdown("👋 Bonjour et bienvenue sur cette application qui vous servira à évaluer votre bien immobilier sur la ville de LYON")
st.caption("Les données utilisées proviennent de la période entre le 01 Juillet 2017 et le 30 Juin 2022")
st.subheader('veuillez entrer les différentes caractéristiques de votre bien')



#create a form
with st.form(key='input_data') :
    col1, col2, col3, col4 = st.columns(4)
    with col1 :
        number = st.number_input('Entrez le numéro de votre adresse',value = 45, step = 1 )
    with col2 :
        name = st.text_input("Entrez le nom de la rue", value = "rue de la bourse")
    with col3 :
        post = st.number_input("Entrez le code postal de votre bien", value = 69002, min_value = 69000, max_value = 69009, step = 1)
    with col4 :
        diag_input = st.selectbox(
        "Quel est le diagnostic énérgétique de votre bien ?",    
        ("A","B","C","D","E","F","G"))

    col5, col6, col7, col8 = st.columns(4)
    with col5 :
        apoumaiz = st.selectbox(
        'Votre bien est il un Appartement ou une Maison ?', 
        (APPARTMENT, HOUSE))
    with col6 :
        number_room = st.number_input("Combien de pièce votre bien possède-t-il ?", value = 1, min_value = 1, max_value = 21, step = 1)
    with col7 : 
        surface = st.number_input("Quelle est la surface habitable ?", value = 0, step = 1)
    with col8 :
        year_input = st.number_input("Quelle est l'année de construction de votre bien ?", value = 1900, min_value = 1900, max_value = 2022, step = 1)

    submitButton = st.form_submit_button(label = 'Envoyer')

pl_plot = st.empty()

if submitButton : # we show the map only after pushing the submit button
    adress = str(number) + " " + name

    # requesting API Nominatim
    locations = requests.get(END_NOMINATIM+"search", params={'city':"LYON", "street" : adress, "postalcode" : post, "country" : "FRANCE", "format":"json"} ).json() 

    for location in locations :
        if location["osm_type"] == "node":
            place = location
        else :
            st.error("l'adresse mentionnée comporte une faute, veuillez rentrer la bonne adresse", icon="🚨")

    point1 = (float(place["lat"]), float(place["lon"])) # coordinates latitude and longitude

    list_gps = []
    for longitude, latitude in zip(df.longitude, df.latitude):
        list_gps.append((latitude, longitude))

    df['tuple_gps'] = list_gps

    my_dist = []
    for coordinate in df.tuple_gps:
                #print(count)
                point2 = coordinate
                result = GRC(point1,point2).m # calculate distance between point 1 and point 2
                result = round(result,2)
                my_dist.append(result)
    df["distance"] = my_dist

    # show different map depending on the type of the real estate : flat or house
    df_map = df.filter(items = ["distance", "valeur_fonciere","latitude", "longitude","type_local","surface_reelle_bati"],)
    if apoumaiz == APPARTMENT :
        mask_appart = df_map['type_local'] == APPARTMENT
        df_map = df_map[mask_appart]
    else :
        mask_house = df_map["type_local"] == HOUSE
        df_map = df_map[mask_house]

    df_map = df_map.sort_values(by = ["distance"], ascending = True)
    df_map = df_map[:10]

    # show the map
    fig = px.scatter_mapbox(df_map, lat="latitude", lon="longitude", 
        mapbox_style = 'carto-positron', 
        color="valeur_fonciere", 
        size="valeur_fonciere", 
        title="Carte comprenant les 10 plus proches ventes par rapport à votre bien",
        hover_data={"latitude": False, "longitude" : False, "surface_reelle_bati" : True },
        center={"lat":float(place["lat"]),"lon":float(place["lon"])},
        color_continuous_scale=px.colors.cyclical.IceFire, size_max=15, zoom=14)

    #send the plotly chart to its spot "in the line" 
    with pl_plot :
        st.plotly_chart(fig, use_container_width=True)

        dico_input = {"type_batiment" : apoumaiz,
                "num_piece" : number_room,
                "surface" : surface,
                "code_postal" : post,
                "long" : float(place["lon"]),
                "lat" : float(place["lat"]),
                "diag" : diag_input,
                "annee_construction" : year_input}

    #Using the model with the data inputed
    param = dico_input
    r = requests.post(MODEL_FINAL, data = json.dumps(param).encode("utf-8"))
    result = r.json()
    prix = int(result['prediction'])
    prix = re.sub("(\d)(?=(\d{3})+(?!\d))", r"\1 ", "%d" % prix)
        
    # Show the prediction
    st.markdown("""
    <style>
    .big-font {
    font-size:75px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<p class="big-font">la valeur de votre bien est estimée à ' + prix + ' €</p>', unsafe_allow_html=True)
    