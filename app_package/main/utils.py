from ct01_models import sess, Users, CaffeineLog
import os
from flask_login import login_required, login_user, logout_user, current_user
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta

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


# returns drink_ios dict item from ios sent data
def get_drink_ios_from_id(drink_api_id_to_check, drinks_ios):
    print("- in get_drink_ios_from_id -")
    for drink in drinks_ios:
        if drink.get('id') == drink_api_id_to_check:
            print(f"drink is: {drink}")
            print(type(drink))
            return drink


def ios_date_converter(ios_date_obj):
    unix_epoch = datetime(2001, 1, 1) # Unix epoch, the starting point of time for Unix systems
    
    # Convert the Swift Language Date double to a datetime object
    datetime_obj = unix_epoch + timedelta(seconds=ios_date_obj)
    print("converted ios_date obje: ", datetime_obj)
    return datetime_obj

def update_drinks_api_with_drinks_ios(current_user, drinks_ios):
    logger_main.info(f"- accessed update_drinks_api_with_drinks_ios ")

    drinks_api = sess.query(CaffeineLog).filter_by(user_id = current_user.id).all()
    
    
    update_flag = False
    # check API drinks are equal to iOS drinks
    for drink_api in drinks_api:
        drink_api_id_to_check = drink_api.id
        drink_ios = get_drink_ios_from_id(drink_api_id_to_check, drinks_ios)

        print(f"drink_ios is: {type(drink_ios)}")
        print(drink_ios)
        if drink_ios == None:
            print(f"- delete drink: {drink_api.id}")
            sess.query(CaffeineLog).filter_by(id=drink_api.id).delete()
            sess.commit()
            continue
        for key, value in drink_ios.items():
            if key == "time_stamp_ios":
                value = ios_date_converter(value)
                print(f"converted ios_date value: {value}")
            if getattr(drink_api, key) != drink_ios.get(key):
                setattr(drink_api,key, value)
                update_flag = True
                logger_main.info(f"- {value} is different, changing it to {key} ")

        if update_flag:
            sess.commit()

def add_missing_drink_api_with_drink_ios(current_user, drinks_ios):

    logger_main.info(f"- accessed add_missing_drink_api_with_drink_ios ")

    drinks_api = sess.query(CaffeineLog).filter_by(user_id = current_user.id).all()
    drinks_api_ids = [drink_api.id for drink_api in drinks_api]
    
    print(f"Drink API ids: {drinks_api_ids}")

    update_flag = False

    for drink_ios in drinks_ios:
        if drink_ios.get('id') not in drinks_api_ids:
            print("- drink_ios.id not found in drinks_api_ids: ", drink_ios.get('id'))
            logger_main.info(f"- atttempting to add drink ")
            if drink_ios.get('time_stamp_ios'):
                drink_ios['time_stamp_ios'] = ios_date_converter(drink_ios['time_stamp_ios'])
            new_drink = CaffeineLog(**drink_ios)
            sess.add(new_drink)
            sess.commit()

