# LolPredict

LolPredict is a player-driven web application for detailed analytics and game prediction for the popular online multiplayer online battle arena (MOBA) game, League of Legends. This website was created during eight weeks of study in The Data Incubator, and was part of my capstone project. The goals of this project was to demonstrate the following:

A clear business objective: LolPredict's data analytics and insights are created for both casual and professional players of League of Legends. The business rationale is that competitive online gaming and esports have recently become internationally appealing and multi-million dollar industries, boasting around 200 million viewers a year and a projected increase of 40% in the following 3 years. So there is a huge monetary incentive for professional and casual players to learn and improve their gameplay via the detailed analytics provided by this website.

Data ingestion: This project involved loading 100,000 matches gathered from calls to the Riot Games API via python's requests module. Another 800,000 data samples loaded from a CSV file (matches pre-gathered from the Riot API by Dorran's Lab, a League of Legends data science group at North Carolina State University).

Visualizations: Analytical graphs of player metrics were generated with matplotlib and plotly. The website includes two distinct types of graphs: bar plots and a radar/roseplot.

A demonstration of at least one of the following:
Machine learning: The underlying game predictor is based on a logistic regression classifier trained on the 100,000 matches pulled from the game's API. Features such as a player's average gold generation, damage to enemy champions, etc. were included in the model. The model was trained using GridSearchCV to find the optimal hyperparameters.
An interactive website: The user-facing component of the project is an interactive website powered by python flask and HTML. It features a game predictor that allows for a user to input their account name, impending champion they will play, and impending opponent champion. The underlying logistic regression classifier will output a win/loss prediction as well as the likelihood of this prediction. Players can also examine how their performance compares to that of the average player in the provided radarplot.

A deliverable: The deliverable is the website that contains the game analytics and predictions.
