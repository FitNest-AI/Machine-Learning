from flask import Flask, jsonify , request
from flask_pymongo import PyMongo
from bson import ObjectId
import jwt
from datetime import datetime
import json
from sklearn.neighbors import NearestNeighbors
import pandas as pd
import numpy as np


app = Flask(__name__)
app.config['MONGO_URI'] = 'mongodb+srv://fitnest:fitnest151123@mycluster.ywz1xtt.mongodb.net/fitnest_db?retryWrites=true&w=majority'
mongo = PyMongo(app)

@app.route('/', methods=['GET'])
def is_login():
    # token = request.headers.get('Authorization')
    token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY1N2UxY2FkZWM1ODRiOGMzMjNmODc2MCIsImlhdCI6MTcwMjk3MTg0MCwiZXhwIjoxNzM0NTA3ODQwfQ.Ov1IJYOQenIrIPi4U6T3ClSd3Wg4Y5hzQKwVt5IJUAs'
    secret_key = 'dd8ef424f64d2f12f965b8e1c039cd301745b58f9a6382f4c2fd4a594db2d5fc0489ce1cd081e2781af9f09b06bff07d4ddc840ababaca31423b88b66df1e60e'
    decoded_token = jwt.decode(token, secret_key, algorithms=['HS256'])
    
    profile= mongo.db.profiles.find_one({'userId': ObjectId(decoded_token['id'])})

    weight= profile['weight']
    height= profile['height']
    dateOfBirth = profile['dateOfBirth']
    bmi= profile['bmi']
    diet = mongo.db.diet_prefs.find_one()

    datenow = datetime.now()
    age = datenow.year - dateOfBirth.year

    if dateOfBirth.month > datenow.month or (dateOfBirth.month == datenow.month and dateOfBirth.day > datenow.day):
        age = age - 1

    bmr = "{:.1f}".format(88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age))

    calories = "{:.1f}".format(float(bmr) * 1.2)

    carbs = "{:.1f}".format(float(calories) * 45/100)

    fat =(1.20 * bmi) + (0.23 * age) - 5.4

    protein = "{:.1f}".format(float(weight) * 0.8)

    types = 0 if diet['name'] != "non vegan" else 1
    recomendation = get_recomendation([float(nutrition) for nutrition in  [calories,carbs,fat,protein,types]], 5)
    return recomendation


def get_recomendation(user_data:list,amount:int):
    """Get the recomendation for the user based on the user data
    Args:
        user_data (list): The user data [calories,carbs,fat,protein,type]
        amount (int): The amount of recomendations
    Returns:
        json: The recomendation in json format
        """     
    # Load the dataset
    main = pd.read_csv('https://storage.googleapis.com/developmentfitnest-bucket/Dataset/food.csv')
    df = main.copy()
    #filter
    if int(user_data[4]) != 0:
        df = df[df['type'] == int(user_data[4])]
    #clear
    main["label"] = main["label"].str.replace(" (","(").str.split("(").str[0]
    
    #add image url
    url = []
    for food in main['label']:
        url.append("https://https://github.com/FitNest-AI/Machine-Learning/blob/main/Datasets/Tracker/images/" 
                   + food.lower().replace(" ", "%20") + ".jpg")
    main["label_link"] = url

    y = df.pop('label')
    X = df.values
    model = NearestNeighbors(n_neighbors=amount, algorithm='ball_tree')
    model.fit(X)
    
    #data
    user_data = np.array(user_data).reshape(1, -1)
    _, indices = model.kneighbors(user_data)
    recommended_foods = main.iloc[indices[0]]
    data = json.dumps(recommended_foods.to_dict(orient='records'), indent=4)
    return data

if __name__ == '__main__':
    app.run(debug=True)



