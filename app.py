from flask import Flask, render_template, request, redirect
import plotly
import plotly.graph_objs as go
import matplotlib.pyplot as plt
import io
import base64

import pandas as pd
import numpy as np
import sklearn

import json
import boto3
import sys

import cassiopeia as cass
from cassiopeia import Champion, Champions
import time
import requests
import pickle
import os

if sys.version_info[0] < 3: 
    from StringIO import StringIO # Python 2.x
else:
    from io import StringIO # Python 3.x

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])

def index():
    
    if request.method == 'POST':
        sumNameText = request.form['summonerName']
        champNameText = request.form['champName']
        oppChampNameText = request.form['oppChampName']
        
        processed_sumName = sumNameText.upper()
        processed_champName = champNameText.capitalize()
        processed_oppChampName = oppChampNameText.capitalize()
        
        # load champion names and IDs
#        dfChampNames = pd.DataFrame(columns=['champion_name','champion_ID'])
#        champions = Champions(region="NA")
#        index = 0
#        for champion in champions:
#                dfChampNames.loc[index] = [champion.name, champion.id ]
#                index+=1
        aws_id = os.environ['AWS_ID']
        aws_secret = os.environ['AWS_SECRET']
        
        client = boto3.client('s3', aws_access_key_id=aws_id,
                aws_secret_access_key=aws_secret)

        bucket_name = 'lolpredict'
        object_key = 'champNamesDf.sav'
        
        dfChampNames = getBucketModel(client,bucket_name,object_key)
        
        # GRAB AND PROCESS DATA
        
        role = 'supp'
        columns2Keep = ['champion_name','match_rank_score','max_time','goldearned','wardsplaced','damagedealttoobjectives',
            'damagedealttoturrets','kda','totaldamagedealttochampions', 'totaldamagetaken', 'totalminionskilled',
            'opp'+role]
        
        dfPlayer,dataYPlayer = getPlayerData(processed_sumName, dfChampNames, role)
        dataX, dataY = getGeneralData(columns2Keep)
        
        pred,prob,sortedInds = predictGame(dfPlayer, processed_champName, processed_oppChampName, columns2Keep)
        
        if pred == 1:
            predStr = 'WIN'
        else:
            predStr = 'LOSS'

        # MAKE PLOTS
        radarplot = create_plot(dfPlayer, dataX, columns2Keep)
        compBarPlotURL = create_comparisonBars(dfPlayer, dataX, columns2Keep, sortedInds)
        
        # RETURN PROCESSED VARIABLES AND RENDER HTML
        
        if pred == -1:
            predictText = "You don't have a previous game played with {champName} against {oppChampName} for us to analyze!".format(champName = processed_champName, oppChampName = processed_oppChampName)
            champImgLink = "https://ddragon.leagueoflegends.com/cdn/9.13.1/img/champion/{}.png".format(processed_champName)
            
            return render_template("parallax.html/",predictResult = predictText, champImgLink = champImgLink, champName = processed_champName)
        
        else:
            predictText = "We are predicting your next game with <b> {champName} </b> will be a <b> {gameOutcome} </b> with a <b> {gameProb}% </b> Chance!".format(champName = processed_champName,gameOutcome = predStr,gameProb = round(prob))
            champImgLink = "https://ddragon.leagueoflegends.com/cdn/9.13.1/img/champion/{}.png".format(processed_champName)
           
            return render_template("parallax.html/",predictResult = predictText, champImgLink = champImgLink, champName = processed_champName, plot=radarplot, compBarPlot = compBarPlotURL.decode('utf8'), plotPlayerDat = 1)
    
    else:   
        champImgLink = 'https://www.publicdomainpictures.net/pictures/40000/nahled/question-mark.jpg'
        return render_template('parallax.html',predictResult = "Input your account name, champion name, and opponent's champion name", champImgLink = champImgLink, plotPlayerDat = 0)


## Get account details by providing the account name
def requestSummonerData(summonerName, APIKey):
    URL = "https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/" + summonerName + "?api_key=" + APIKey
    response = requests.get(URL)
    return response.json()

## Get an account's ranked match data by account ID
def requestRankedData(ID, APIKey):
    URL = "https://na1.api.riotgames.com/lol/summoner/v4/positions/by-summoner/" + str(ID) + "?api_key=" + APIKey
    response = requests.get(URL)
    return response.json()

def requestMatchList(ID, APIKey):
    URL = "https://na1.api.riotgames.com/lol/match/v4/matchlists/by-account/" + str(ID) + "?api_key=" + APIKey
    response = requests.get(URL)
    return response.json()

def requestMatchInfo(matchID, APIKey):
    URL = "https://na1.api.riotgames.com//lol/match/v4/matches/" + str(matchID) + "?api_key=" + APIKey
    response = requests.get(URL)
    return response.json()

def getBucketModel(client,bucket_name,object_key):
    csv_obj = client.get_object(Bucket=bucket_name, Key=object_key)
    body = csv_obj['Body']
    csv_string = body.read()
    return pickle.loads( csv_string )

def getBucketFile(client,bucket_name,object_key):
    csv_obj = client.get_object(Bucket=bucket_name, Key=object_key)
    body = csv_obj['Body']
    csv_string = body.read().decode('utf-8')
    return pd.read_csv(StringIO(csv_string))

################## BELOW ARE ANALYSIS METHODS

def getGeneralData(columns2Keep):
     #load general player data pulled from API
    # get your credentials from environment variables
    aws_id = os.environ['AWS_ID']
    aws_secret = os.environ['AWS_SECRET']
    
    client = boto3.client('s3', aws_access_key_id=aws_id,
            aws_secret_access_key=aws_secret)
    
    bucket_name = 'lolpredict'
    object_key = 'supp_playerDB_cleaned.csv'
    
    data = getBucketFile(client,bucket_name,object_key)

    # process overall player data
    data.columns = data.columns.str.strip().str.lower().str.replace(' ', '_')
    dataX_all=data.drop('win',axis=1)
    dataX = dataX_all[columns2Keep]
    dataY=data['win']
    
    return dataX, dataY

def getPlayerData(sumName,dfChampNames,role):
    # define columns to analyze

    #load general player data pulled from API
    # get your credentials from environment variables
    aws_id = os.environ['AWS_ID']
    aws_secret = os.environ['AWS_SECRET']
    
    client = boto3.client('s3', aws_access_key_id=aws_id,
            aws_secret_access_key=aws_secret)

    # add code for pulling data from riot API for other players

    bucket_name = 'lolpredict'
    object_key = 'player.csv'
    dfPlayer = getBucketFile(client,bucket_name,object_key)
    #dfPlayer = pd.read_csv("I:\\Users\\The Iron Maiden\\Documents\\GitHub\\DIChallenge\\player.csv")
    
    object_key = 'player_y.csv'
    dataYPlayer = getBucketFile(client,bucket_name,object_key)
    
    #dataYPlayer = pd.read_csv("I:\\Users\\The Iron Maiden\\Documents\\GitHub\\DIChallenge\\player_y.csv")
    dfPlayer = dfPlayer.drop('player'+role,axis=1) # TEMPORARY UNTIL REMOVE THAT COLUMN
    
    return dfPlayer,dataYPlayer

def predictGame(dfPlayer, processed_champName,processed_oppChampName,columns2Keep):
    
    aws_id = os.environ['AWS_ID']
    aws_secret = os.environ['AWS_SECRET']
    
    client = boto3.client('s3', aws_access_key_id=aws_id,
            aws_secret_access_key=aws_secret)
    bucket_name = 'lolpredict'
    
    columns_to_encode_champName = ['champion_name']
    columns_to_encode_oppChamp = ['oppsupp']
    columns_to_scale  = columns2Keep[1:-1]
    numVars = len(columns_to_scale)
    
    #processed_champName = 'Veigar'
    #processed_oppChampName = 'Pyke'
    
    #### Load pickled ML feature transformers
    object_key = 'final_logRegLoL.sav'
    loaded_model = getBucketModel(client,bucket_name,object_key)
    logCoefs_abs = abs(loaded_model.coef_)
    logCoefs_absSort = sorted(logCoefs_abs[0,0:numVars],reverse=True)
    sortedInds = np.argsort(-logCoefs_abs[0,0:numVars])
    
    object_key = 'ohe_lolpredict.sav'
    ohe = getBucketModel(client,bucket_name,object_key)
    
    object_key = 'oheOpp_lolpredict.sav'
    oheOpp = getBucketModel(client,bucket_name,object_key)

    object_key = 'scaler_lolpredict.sav'
    scaler = getBucketModel(client,bucket_name,object_key)
    
    checkPresence = (dfPlayer['champion_name'] == processed_champName) & (dfPlayer['oppsupp'] == processed_oppChampName)
    print(sum(checkPresence))
    if sum(checkPresence) > 0:
    
        rowData = dfPlayer.loc[checkPresence].iloc[0]
        encoded_playerChamp =    ohe.transform(rowData[columns_to_encode_champName].values.reshape(1, -1))
        encoded_oppChamp =       oheOpp.transform(rowData[columns_to_encode_oppChamp].values.reshape(1, -1))
        scaled_columns_player  = scaler.transform(rowData[columns_to_scale].values.reshape(1, -1) )
        
        toPredict = np.concatenate((scaled_columns_player, encoded_playerChamp,encoded_oppChamp), axis=1) 
        
        # calculate predicted probability
        pred = int( loaded_model.predict(toPredict) )
        prob = float( loaded_model.predict_proba(toPredict)[:,1] )*100
    else:
        pred = -1; prob = 0
        
    return pred, prob, sortedInds
    
def create_plot(dfPlayer,dataX,columns2Keep):

    role = 'supp'
    
    # append column for data group
    tmpData = dataX.drop('champion_name',axis=1).drop('opp'+role,axis=1).assign(Group='data')
    tmpDataPlayer = dfPlayer.drop('champion_name',axis=1).drop('opp'+role,axis=1).assign(Group='player')
    allDataWithPlayer = tmpData.append(tmpDataPlayer, ignore_index=True)
    
    # normalize (0-1) ccontinuous data and add back on group
    df_2norm = allDataWithPlayer.iloc[:,1:-1]
    normalized_df=( df_2norm-df_2norm.min() )/( df_2norm.max()-df_2norm.min() )
    normalized_df['Group']=allDataWithPlayer['Group']
    
    col2Group = columns2Keep[1:-1]
    justDataData = normalized_df.loc[normalized_df['Group'] == 'data']
    norm_dataMean = justDataData[0:1000].mean(axis=0)
    norm_playerMean = normalized_df.loc[normalized_df['Group'] == 'player'].mean(axis=0)
    
    topThree = (norm_playerMean - norm_dataMean).sort_values(ascending=False).head(3)
    
    categories = columns2Keep[1:-1]
    
    columns2Keep = ['Player Rank','Game Time','Gold Earned','Wards Placed','Damage to Objectives',
            'Damage to Turrets','KDA','Damage to Champions', 'Damage Taken', 'Minions Killed',
            ]
    
    # guide on using flask and plotly: https://code.tutsplus.com/tutorials/charting-using-plotly-in-python--cms-30286
    polar_player = go.Scatterpolar(
          r=norm_dataMean,
          theta=columns2Keep,
          fill='toself',
          name='Average Player Performance'
    )
    
    polar_general = go.Scatterpolar(
          r=norm_playerMean,
          theta=columns2Keep,
          fill='toself',
          name='Your Performance'
    )
        

    data = [polar_player, polar_general]
    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
    
    
    return graphJSON

def create_comparisonBars(dfPlayer,dataX,columns2Keep,sortedInds):
    
    img = io.BytesIO()
    
    columns_to_scale  = columns2Keep[1:-1]
    
    topThreeFeatures = [columns_to_scale[i] for i in sortedInds][:3]

    topThreePlayer = dfPlayer[topThreeFeatures].mean(axis=0)
    topThreeData = dataX[topThreeFeatures].mean(axis=0)
    
    # append column for data group
    tmpData = dataX.drop('champion_name',axis=1).drop('oppsupp',axis=1).assign(Group='data')
    tmpDataPlayer = dfPlayer.drop('champion_name',axis=1).drop('oppsupp',axis=1).assign(Group='player')
    allDataWithPlayer = tmpData.append(tmpDataPlayer, ignore_index=True)
    
    topThreeAll = allDataWithPlayer[topThreeFeatures].mean(axis=0)
    stdDevThree_player = allDataWithPlayer[topThreeFeatures].std(axis=0)/2
    ylimLow = topThreeAll - stdDevThree_player
    ylimHigh = topThreeAll + stdDevThree_player 

    xLabels=['Your Performance', 'Average Player']
    tmpTitles = ['Kill/Death/Assist Ratio', 'Gold Earned', 'Damage to Turrets']
    tmpYlab = ['KDA Ratio','Gold','Damage Units']
    tmpYlim = [ [0,5.5],[6000,9000],[1000,1700] ]
    
    fig2, axs = plt.subplots(1, 3,figsize=(18,4))
    
    x_pos = np.arange(len(xLabels))
    
    for i in range(3):
    
        axs[i].bar(x_pos[0], topThreePlayer[i], align='center', alpha=0.8)
        axs[i].bar(x_pos[1], topThreeData[i], align='center', alpha=0.8)
        axs[i].set_title(tmpTitles[i], fontsize = 20)
        axs[i].set_ylabel(tmpYlab[i], fontsize = 15)
        axs[i].set_ylim(tmpYlim[i])
        
        axs[i].set_xticks(x_pos)
        axs[i].set_xticklabels(xLabels, rotation=0, fontsize=15)

    plt.savefig(img, format='png')
    plt.close()   
    img.seek(0)

    return base64.b64encode(img.getvalue())

@app.route('/about')
def about():
  return render_template('about.html')

if __name__ == '__main__':
  app.run(port=33507)
