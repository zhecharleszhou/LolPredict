from flask import Flask, render_template, request, redirect
import plotly
import plotly.graph_objs as go
import pandas as pd
import numpy as np
import json

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])

def index():
    
    if request.method == 'POST':
        sumNameText = request.form['summonerName']
        champNameText = request.form['champName']
        processed_sumName = sumNameText.upper()
        processed_champName = champNameText.capitalize()
        
        bar = create_plot()
        
        return render_template("parallax.html/",result = processed_champName, plot=bar)
    else:    
        return render_template('parallax.html')

#def predictGame():
#    data=pd.read_csv("C:\\Users\\The Iron Maiden\\Documents\\DataScienceProjects\\supp_playerDB_cleaned.csv")

def create_plot():
    
    # define columns to analyze
    role = 'supp'
    columns2Keep = ['champion_name','match_rank_score','max_time','goldearned','wardsplaced','damagedealttoobjectives',
                    'damagedealttoturrets','kda','totaldamagedealttochampions', 'totaldamagetaken', 'totalminionskilled',
                    'opp'+role]
    
    # load overall player data
    data=pd.read_csv("C:\\Users\\The Iron Maiden\\Documents\\DataScienceProjects\\supp_playerDB_cleaned.csv")
    data.columns = data.columns.str.strip().str.lower().str.replace(' ', '_')
    dataX_all=data.drop('win',axis=1)
    dataX = dataX_all[columns2Keep]
    dataY=data['win']
    
    # load player data
    dfPlayer = pd.read_csv("I:\\Users\\The Iron Maiden\\Documents\\GitHub\\DIChallenge\\player.csv") 
    dataYPlayer = pd.read_csv("I:\\Users\\The Iron Maiden\\Documents\\GitHub\\DIChallenge\\player_y.csv")
    dfPlayer = dfPlayer.drop('player'+role,axis=1) # TEMPORARY UNTIL REMOVE THAT COLUMN
    
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
    
    categories = columns2Keep[1:-1]
    
    # guide on using flask and plotly: https://code.tutsplus.com/tutorials/charting-using-plotly-in-python--cms-30286
    polar_player = go.Scatterpolar(
          r=norm_dataMean,
          theta=categories,
          fill='toself',
          name='Average Player Performance'
    )
    
    polar_general = go.Scatterpolar(
          r=norm_playerMean,
          theta=categories,
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
