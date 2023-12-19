from flask import Flask, jsonify
from flask_pymongo import PyMongo
from bson import ObjectId
import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
app.config['MONGO_URI'] = os.getenv("MONGO_URI")
mongo = PyMongo(app)

LEVEL_MULTIPLIER = {
    'easy': 1,
    'medium': 2,
    'hard': 3,
}

@app.route('/', methods=['GET'])
def getWorkout():
    workouts = mongo.db.workouts.find()
    result = [
        {
            '_id': str(workout['_id']), 
            'name': workout['name'], 
            'desc': workout['desc'],
            'rest': workout['rest'],
            'day': workout['day'],
            'time': workout['time'],
            'level': get_most_common_level(workout['moveset']),
            'point': calculate_points_by_target_muscle(workout['moveset']),
            'moveset': [
                {
                    'rep': move['rep'],
                    'set': move['set'],
                    'exerciseId': get_exercise_data(move['exerciseId'])
                } for move in workout['moveset']
            ],
            'userId': str(workout['userId']),
        } for workout in workouts
    ]
    
    datas = [(data['point'],data['level']) for data in result]
    result = get_recommendation(result,datas,"easy")[0]
    
    response = {
        'success': True,
        'message': 'Workout all data fetch successful',
        'data': {
            'workout': result,
            'count': len(result)+1,
            
        }
    }
    
    return jsonify(response)

def get_recommendation(database:list,workout_list : list,level : str = "easy",
                       target : str = "abs",amount : int = 1):
    
    
    #this is some data manipulation thingy
    temporary = []
    for index,data in enumerate(workout_list):
        temp_dict = data[0]
        temp_dict['level'] = data[1]
        temp_dict['index'] = index
        temporary.append(temp_dict)
       
    df = pd.DataFrame(temporary)
    main = df.copy()
    
    #Level filter , only exclusive to easy , medium = easy + medium , 
    # hard = easy + medium + hard
    
    #change it if you want to change the exclusiveness
    main = main.drop("index",axis=1)
    match level:
        case "easy":
            main = main[main['level'] == "easy"]
        case "medium":
            main = main[main['level'] != "hard"]
    
    main = main.drop(['level'],axis=1)
    target_muscle = main.columns.tolist()
    #get the target muscle's mean
    
    #generate user data by target
    user_data = []
    for muscle in target_muscle:
        target_muscle_mean = 0
        if muscle == target:
            target_muscle_mean = df[muscle].mean()
        user_data.append(target_muscle_mean)
    
    X = main.values
    model = NearestNeighbors(n_neighbors=amount,algorithm='ball_tree')
    model.fit(X)
    _,indices = model.kneighbors([user_data])
    return [database[index] for index in indices[0]]

def get_exercise_data(exercise_id):
    exercise = mongo.db.exercises.find_one({'_id': ObjectId(exercise_id)})
    if exercise:
        return {
            '_id': str(exercise['_id']),
            'name': exercise['name'],
            'desc': exercise['desc'],
            'image': exercise['image'],
            'levelId': get_level_data(exercise['levelId']),
            'targetMuscleId': get_target_muscle_data(exercise['targetMuscleId']),
            'direction': exercise['direction'],
            'orientation': exercise['orientation'],
            'instruction': exercise['instruction'],
            'start': exercise['start'],
            'end': exercise['end'],
        }
    else:
        return None

def get_level_data(level_id):
    level = mongo.db.levels.find_one({'_id': ObjectId(level_id)})
    if level:
        return {
            '_id': str(level['_id']),
            'name': level['name'],
        }
    else:
        return None

def get_target_muscle_data(target_muscle_ids):
    result = []
    for target_muscle_id in target_muscle_ids:
        target_muscle = mongo.db.target_muscles.find_one({'_id': ObjectId(target_muscle_id)})
        if target_muscle:
            result.append({
                '_id': str(target_muscle['_id']),
                'name': target_muscle['name'],
            })

    return result if result else None

def get_most_common_level(moveset):
    levels = [get_exercise_data(move['exerciseId'])['levelId']['name'] for move in moveset]
    result = {}
    
    for level in levels:
        result[level] = result.get(level, 0) + 1
    
    most_common_level = max(result, key=result.get, default=None)
    
    return most_common_level

def calculate_points_by_target_muscle(moveset):
    points_by_target_muscle = {}

    for move in moveset:
        exercise_data = get_exercise_data(move['exerciseId'])
        target_muscles = exercise_data.get('targetMuscleId', [])
        level_data = exercise_data.get('levelId', {})
        level_name = level_data.get('name', 'easy')
        level_number = LEVEL_MULTIPLIER.get(level_name, 1)

        # Fetch all target muscles from the database
        target_muscle_non = mongo.db.target_muscles.find()

        # Initialize points for all target muscles with 0
        for target_muscle in target_muscle_non:
            target_muscle_name = target_muscle['name']
            points_by_target_muscle.setdefault(target_muscle_name, 0)

        for target_muscle in target_muscles:
            target_muscle_name = target_muscle['name']
            rep = move['rep']
            set_count = move['set']
            points = (rep * set_count) * level_number

            # Update points for the specific target muscle
            points_by_target_muscle[target_muscle_name] += points


    return points_by_target_muscle


if __name__ == '__main__':
    app.run(debug=True)