from flask import Blueprint
from flask import render_template, jsonify, request
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from ct01_models import sess, Users, CaffeineLog
from flask_login import login_required, login_user, logout_user, current_user
from app_package.token_decorator import token_required
from app_package.main.utils import update_drinks_api_with_drinks_ios, \
    add_missing_drink_api_with_drink_ios, ios_date_converter

main = Blueprint('main', __name__)

formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

logger_main = logging.getLogger(__name__)
logger_main.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(os.path.join(os.environ.get('WEB_ROOT'),'logs','main_routes.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

logger_main.addHandler(file_handler)
logger_main.addHandler(stream_handler)


@main.route("/check_status", methods=["GET","POST"])
def check_status():
    logger_main.info(f"-- in check_status --")
    today_string = datetime.now().strftime("%c")
    status_message = f"Running as of {today_string}"
    print(status_message)
    return jsonify({"status":status_message})


@main.route("/check_auth", methods=["GET"])
@token_required
def check_auth(current_user):

    return jsonify({"status": f"logged in as {current_user.email} -- success!"})



@main.route("/caffeine_log_update_new", methods=["POST"])
@token_required
def caffeine_log_update_new(current_user):
    logger_main.info(f"- accessed /caffeine_log_update_new ")

    try:
        request_json = request.json
    except Exception as e:
        print("failed reqeust.json")
        logger_main.info(e)
        return jsonify({"status": "httpBody data recieved not json not parse-able."})

    #NOTE: This works from jupyter notebook -- might not work from swift app --> user caffeine_log_update route
    existing_log = sess.query(CaffeineLog).filter_by(uuid = request_json.get('uuid')).first()
    if not existing_log :
        new_log = CaffeineLog(user_id=current_user.id)
        for key, value in request_json.items():
            if key == 'time_stamp_ios':
                # print(f"time_stamp_ios: {value}")
                # unix_epoch = datetime(2001, 1, 1) # Unix epoch, the starting point of time for Unix systems

                # # Convert the Swift Language Date double to a datetime object
                # date_time_ios = unix_epoch + timedelta(seconds=value)
                datetime_obj = ios_date_converter(value)
                print("Converted to today:", datetime_obj) # Output the datetime object
                # date_time_ios = datetime.strptime(date_time,"%Y-%m-%d %H:%M:%S.%f")
                setattr(new_log,key, datetime_obj)
            # NOTE: drink_logs come in as dictionaries with their data types intact -- super useful!
            if key not in ['id','user_id','time_stamp_ios']:
                setattr(new_log,key,value)
            
            
        sess.add(new_log)
        sess.commit()
        print(f"Log ID: {new_log.id}, has been added!")
    else:
        print(f"UUID: {existing_log.uuid}, already exists in database.")
    

    return jsonify({"status":"successfully updated caffeine log", "drink_id":str(new_log.id)})


@main.route("/user", methods=["GET","POST"])
def user():
    logger_main.info(f"-- in user rounte --")

    data_headers = request.headers

    try:
        request_json = request.json
        print("request_json:",request_json)
    except Exception as e:
        logger_main.info(e)
        return jsonify({"status": "httpBody data recieved not json not parse-able."})

    print("*** Do we get here?")
    existing_user = sess.query(Users).filter_by(email=request_json.get('email')).first()
    print(f"the exisitng user is: {existing_user}")
    if not existing_user:
        logger_main.info(f"-- NO, existing_user found --")
        # add user to db
        new_user = Users()
        
        for i,j in request_json.items():
            if i != 'id':
                setattr(new_user,i,j)

        setattr(new_user,"password","password")
        sess.add(new_user)
        sess.commit()
        print("Added new user: ",new_user)
        return jsonify({"id":str(new_user.id), "email":new_user.email,"username":new_user.username})
    
    else:
        logger_main.info(f"-- YES, existing_user found --")
        # print(id:)
        return jsonify({"id":str(existing_user.id),"email":existing_user.email,"username":existing_user.username})


# on sign in to update caffeine log API Database with what is found in the iOS
@main.route("/update_drinks_log", methods=["POST"])
@token_required
def update_drinks_log(current_user):
    logger_main.info(f"- accessed /update_drinks_log ")
    # drinks_api = sess.query(CaffeineLog).filter_by(user_id = current_user.id).all()
    try:
        # ios_drinks_list = request.json
        drinks_ios = request.json
        print("drinks_ios:",drinks_ios)
        # print(type(ios_drinks_list))
        # print(ios_drinks_list[0])
        # print(type(ios_drinks_list[0]))
        # # print("drink[0].id:", ios_drinks_list[0].id)
        # print("---- ios_dkrins_list[0]  keys, values ----")
        # for i,j in ios_drinks_list[0].items():
        #     print(i,j)
        #     if i == 'id':
        #         print("**** Found id wft ??")

    except Exception as e:
        logger_main.info(e)
        return jsonify({"status": "httpBody data recieved not json not parse-able."})

    drinks_ios_ids = [drink_.get('id') for drink_ in drinks_ios]
    print(f"ios_drink_list_drink_ids: {drinks_ios_ids}")

    # check that each drink in drinks_api has same data as drinks_ios
    update_drinks_api_with_drinks_ios(current_user, drinks_ios)


    #check for any drinks_ios missing from drinks_api
    add_missing_drink_api_with_drink_ios(current_user, drinks_ios)


    drinks_api = sess.query(CaffeineLog).filter_by(user_id = current_user.id).all()


    return jsonify({"status":f"Caffeine Tracker API has {len(drinks_api)} logged drinks for user: {current_user.email}"})

@main.route("/caffeine_log_update", methods=["GET","POST"])
def caffeine_log_update():
    logger_main.info(f"- accessed /drinks ")

    try:
        request_json = request.json
        print("request_json:",request_json)
    except Exception as e:
        logger_main.info(e)
        return jsonify({"status": "httpBody data recieved not json not parse-able."})

    for drink_log in request_json:

        # NOTE: drink_logs come in as dictionaries with their data types intact -- super useful!

        existing_log = sess.query(CaffeineLog).filter_by(uuid = drink_log.get('uuid')).first()
        if not existing_log :
            new_log = CaffeineLog()
            for key, value in drink_log.items():
                if key != 'id':
                    setattr(new_log,key,value)
            
            sess.add(new_log)
            sess.commit()
            print(f"Log ID: {new_log.id}, has been added!")
        else:
            print(f"UUID: {existing_log.uuid}, already exists in database.")
    

    return jsonify({"status":"successfully updated caffeine log"})

@main.route("/delete_log_entry", methods=["GET","POST"])
@token_required
def delete_log_entry(current_user):

    try:
        request_json = request.json
        print("request_json:",request_json)
    except Exception as e:
        logger_main.info(e)
        return jsonify({"status": "httpBody data recieved not json not parse-able."})

    uuid_to_delete = request_json.get('uuid_to_delete')
    sess.query(CaffeineLog).filter_by(uuid = uuid_to_delete).delete()
    sess.commit()

    logger_main.info(f"Successfully deleted uuid: {uuid_to_delete}")

    return jsonify({"status":f"Successfully deleted uuid: {uuid_to_delete}"})


@main.route("/test_login", methods=["GET"])
@login_required
def test_login():

    return jsonify({"status":f"User email: {current_user.id} successfully logged in and has access"})
