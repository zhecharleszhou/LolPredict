from flask import Flask, render_template, request, redirect
import plotly
import plotly.graph_objs as go
import pandas as pd
import numpy as np
import json
import boto3
import sys
import cassiopeia as cass
from cassiopeia import Champion, Champions
import time
import requests
import pickle
import os
import sklearn

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
        
        role = 'supp'
        columns2Keep = ['champion_name','match_rank_score','max_time','goldearned','wardsplaced','damagedealttoobjectives',
            'damagedealttoturrets','kda','totaldamagedealttochampions', 'totaldamagetaken', 'totalminionskilled',
            'opp'+role]
        
        dfPlayer,dataYPlayer = getPlayerData(role)
        
        pred,prob = predictGame(dfPlayer, processed_champName,processed_oppChampName,columns2Keep)
        if pred == 1:
            predStr = 'WIN'
        else:
            predStr = 'LOSS'

        radarplot = create_plot(columns2Keep)
        
        return render_template("parallax.html/",result = processed_champName, gameOutcome = predStr, gameProb = str(prob), plot=radarplot)
    else:    
        return render_template('parallax.html',result = '?', gameOutcome = '?', gameProb = '?')


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

def getPlayerData(role):
    # define columns to analyze
    

    #load general player data pulled from API
    # get your credentials from environment variables
    aws_id = os.environ['AWS_ID']
    aws_secret = os.environ['AWS_SECRET']
    
    client = boto3.client('s3', aws_access_key_id=aws_id,
            aws_secret_access_key=aws_secret)
    
    
    ########################### load player data
#    APIKey = os.environ.get('League_API')
#    role = 'supp'
#    rankNames = ['BRONZE',  'SILVER', 'GOLD', 'PLATINUM', 'DIAMOND', 'MASTERS', 'CHALLENGER']
#    columnNames = ['champion_name','match_rank_score','max_time','goldearned','wardsplaced','damagedealttoobjectives',
#                'damagedealttoturrets','kda','totaldamagedealttochampions', 'totaldamagetaken', 'totalminionskilled',
#                'player'+role,'opp'+role]
#    dfPlayer = pd.DataFrame(columns=columnNames)
#    dataYPlayer = pd.Series(name="win")
#    
#    # load champion names and IDs
#    dfChampNames = pd.DataFrame(columns=['champion_name','champion_ID'])
#    champions = Champions(region="NA")
#    index = 0
#    for champion in champions:
#            dfChampNames.loc[index] = [champion.name, champion.id ]
#            index+=1
#    
#    summonerName = 'Duvet Cover'
#    summonerData  = requestSummonerData(summonerName, APIKey)
#    
#    # Uncomment this line if you want a pretty JSON data dump
#    #print(json.dumps(summonerData, sort_keys=True, indent=2))
#    
#    ## Pull the ID field from the response data, cast it to an int
#    ID = summonerData ['id']
#    accountID = summonerData ['accountId']   
#        
#    matchList  = requestMatchList(accountID, APIKey)
#       
#    numMatches = len(matchList ['matches'])
#    
#    for iMatch in range(90):
#    
#        #print( 'Get match'+ str(iMatch) )
#        
#        matchID = matchList ['matches'][iMatch]['gameId'] # get this match's ID
#        
#        matchInfo = requestMatchInfo(matchID, APIKey) # pull this game's info from riotAPI
#                
#        # find index of player in player list
#        for i in range( len(matchInfo['participantIdentities']) ):
#            thisParticipant = matchInfo['participantIdentities'][i]['player']
#            if 'currentAccountId' in thisParticipant:
#                playerAcctId = thisParticipant['currentAccountId']
#            else:
#                playerAcctId = thisParticipant['accountId']
#            if playerAcctId == accountID:
#                playerKey = i
#        
#        if matchInfo['participants'][playerKey]['timeline']['role'] == 'DUO_SUPPORT':
#        
#            try: 
#                statsDict = matchInfo['participants'][playerKey]['stats'] # get stats dict from this game
#                
#            
#                ############ preprocess data
#                
#                # calculate KDA
#                if statsDict['deaths'] == 0:
#                    kda = statsDict['kills'] + statsDict['assists']
#                else:
#                    kda = ( statsDict['kills'] + statsDict['assists'] ) / statsDict['deaths']
#                    
#                # figure out champion name from ID
#                thisChampionID = matchInfo['participants'][playerKey]['championId']
#                tfIndex = dfChampNames['champion_ID'] == thisChampionID
#                champName =  dfChampNames[tfIndex]['champion_name'].item()
#                
#                # figure out player's match rank
#                thisRank = matchInfo['participants'][playerKey]['highestAchievedSeasonTier']
#                matchRank = rankNames.index(thisRank) + 1
#                
#                teamID = matchInfo['participants'][playerKey]['teamId'] 
#                for iParticipant in range(0,10):
#                        thisRole = matchInfo['participants'][iParticipant]['timeline']['role']
#                        thisLane = matchInfo['participants'][iParticipant]['timeline']['lane']
#                        thisTeamID = matchInfo['participants'][iParticipant]['teamId']
#                        
#                        thisPlayerChampionID = matchInfo['participants'][iParticipant]['championId']
#                        champIndex = dfChampNames['champion_ID'] == thisPlayerChampionID
#                        thisChampName =  dfChampNames[champIndex]['champion_name'].item()
#    
#                        tmpID = "{}_{}".format(thisRole,thisLane)
#                        
#                        if tmpID == 'SOLO_TOP' and thisTeamID == teamID: 
#                            playerTop = thisChampName
#                        elif tmpID == 'NONE_JUNGLE' and thisTeamID == teamID:
#                            playerJung = thisChampName
#                        elif tmpID == 'SOLO_MIDDLE' and thisTeamID == teamID:
#                            playerMid = thisChampName
#                        elif tmpID == 'DUO_CARRY_BOTTOM' and thisTeamID == teamID:
#                            playerADC = thisChampName
#                        elif tmpID == 'DUO_SUPPORT_BOTTOM' and thisTeamID == teamID:
#                            playerSupp = thisChampName
#                        elif tmpID == 'SOLO_TOP' and thisTeamID != teamID:
#                            oppTop = thisChampName
#                        elif tmpID == 'NONE_JUNGLE' and thisTeamID != teamID:
#                            oppJung = thisChampName
#                        elif tmpID == 'SOLO_MIDDLE' and thisTeamID != teamID:
#                            oppMid = thisChampName
#                        elif tmpID == 'DUO_CARRY_BOTTOM' and thisTeamID != teamID:   
#                            oppADC = thisChampName
#                        elif tmpID == 'DUO_SUPPORT_BOTTOM' and thisTeamID != teamID: 
#                            oppSupp = thisChampName
#                
#                ############ preprocess data end
#    
#                # create a vector of data to append for this match
#                addVector = [ champName, matchRank, matchInfo['gameDuration'], statsDict['goldEarned'], 
#                             statsDict['wardsPlaced'], statsDict['damageDealtToObjectives'], 
#                             statsDict['damageDealtToTurrets'], kda, 
#                             statsDict['totalDamageDealtToChampions'],
#                             statsDict['totalDamageTaken'],statsDict['totalMinionsKilled'],
#                             eval('player'+role.capitalize()), eval('opp'+role.capitalize())
#                        ]
#                
#                
#                dfPlayer.loc[iMatch] = addVector
#                if statsDict['win'] == True: 
#                    dataYPlayer.loc[iMatch] = 1
#                else: 
#                    dataYPlayer.loc[iMatch] = 0
#            except:
#                print ('Missing fields')
#    
#    # get rid of entries where player champ name doesn't match
#    for index,row in dfPlayer.iterrows():
#        thisRow_champName = row['champion_name']
#        thisRow_playerRole = row['playersupp'] 
#   
#        if thisRow_champName != thisRow_playerRole:
#  
#            dfPlayer = dfPlayer.drop(index)
#            dataYPlayer = dataYPlayer.drop(index)
#            
#    # calculate mean across matches for post-game metrics
#    dfPlayer_shape = dfPlayer.shape    
#    row_index_list = range(0,dfPlayer_shape[0]) # get range for all row indices
#    column_list = columnNames[1:-2] # skip champ name column
#    
#    uniquePlayerChamps = dfPlayer.champion_name.unique()
#    
#    # take mean across continuous columns        
#    for champ in uniquePlayerChamps:
#        
#        tmp = dfPlayer.loc[dfPlayer['champion_name'] == champ]
#        champMean = tmp[column_list].mean(axis=0)
#    
#        # replace all rows of dfPlayer with mean
#        for iRow in tmp.index : # 
#      
#            oppRoleChamp = dfPlayer.loc[iRow]['oppsupp']
#            champMean.at['champion_name'] = champ
#            champMean.at['oppsupp'] = oppRoleChamp
#            dfPlayer.loc[iRow] = champMean
#    
    ##############################################
     
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
    
    processed_champName = 'Veigar'
    processed_oppChampName = 'Pyke'
    
    #### Load pickled ML feature transformers
    object_key = 'final_logRegLoL.sav'
    loaded_model = getBucketModel(client,bucket_name,object_key)
    
    object_key = 'ohe_lolpredict.sav'
    ohe = getBucketModel(client,bucket_name,object_key)
    
    object_key = 'oheOpp_lolpredict.sav'
    oheOpp = getBucketModel(client,bucket_name,object_key)

    object_key = 'scaler_lolpredict.sav'
    scaler = getBucketModel(client,bucket_name,object_key)
    
    checkPresence = (dfPlayer['champion_name'] == processed_champName) & (dfPlayer['oppsupp'] == processed_oppChampName)
    
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
        
    return pred, prob
    
def create_plot(columns2Keep):

    role = 'supp'

    
    dfPlayer,dataYPlayer = getPlayerData(role)
    dataX, dataY = getGeneralData(columns2Keep)
    
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
            'Damage to Turrets','KDA','Damage to Champs', 'Damage Taken', 'Minions Killed',
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

@app.route('/about')
def about():
  return render_template('about.html')

if __name__ == '__main__':
  app.run(port=33507)
