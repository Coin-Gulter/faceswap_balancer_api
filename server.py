import os
import time
import json
import uvicorn
import redis
import requests
import logging

from datetime import datetime, timezone
from dateutil import parser
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse

from schemas import (Request,
                     Status,
                     TemplateUpload,
                     DetectFaceUpload,)

from dotenv import load_dotenv

from server_utils import (get_server_with_less_queue,
                          send_templates_on_nodes,
                          send_detect_face_on_nodes,
                          face_swap_request,
                          error_msg_to_tg)


load_dotenv()

app = FastAPI(title="Balancer API", version="1.0.0")
redis_instance = redis.StrictRedis(host='127.0.0.1', port=int(os.environ.get('REDIS_PORT')), db=0,
                                   password=os.environ.get('REDIS_PASSWORD', ''))

daily_limit = int(os.environ['REQUESTS_NUMBER'])
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@app.post("/face_swap/", response_model=str | dict)
async def create_face_swap_process(request: Request):
    try:
        print('user id - ', request.user_id)
        user_id_user_requests = redis_instance.get(request.user_id)

        if user_id_user_requests is None:
            current_count_user_requests = 0
        else:
            current_count_user_requests = int(user_id_user_requests)

        # if < 3 requests
        if current_count_user_requests < 3:
            print('test request for user id')
            server_list = get_server_with_less_queue()
            
            if server_list:
                response = face_swap_request(server_list, "face_swap/",
                                             headers={'accept': 'application/json', 'Content-Type': 'application/json'},
                                             json_dict={'typeReq': request.typeReq,
                                                        'template_id': request.template_id,
                                                        'faceFrom': request.faceFrom,
                                                        'faceTo': request.faceTo,
                                                        'watermark': True,
                                                        'new': True if current_count_user_requests == 0 else False})

                if 'task_id' in response:
                    redis_instance.incr(str(request.user_id))
                    print('redis increment')

                return response

            else:
                error_msg_to_tg(f"Error!\nSomething wrong with queue servers in /face_swap/ - status_code: {500}")
                return JSONResponse(content={"message": f"Something wrong with queue servers",
                                             "status": "ERROR"},
                                    status_code=500)
        # if >= 3 requests
        else:
            response_about_user_subscription = requests.get(
                f"https://api.apphud.com/v1/customers?api_key={os.environ['API_KEY']}&user_id={request.user_id}").json()

            if response_about_user_subscription['data']['results'] is not None:
                if response_about_user_subscription['data']['results']['subscriptions']:
                    for subscription in response_about_user_subscription['data']['results']['subscriptions']:
                        if subscription['status'] in ['regular', 'trial', 'promo', 'intro']:

                            expires_at = datetime.strptime(subscription["expires_at"], "%Y-%m-%dT%H:%M:%S.%fZ")

                            if datetime.now().timestamp() < expires_at.timestamp():
                                print('premium request for user id')
                                current_time = int(time.time())
                                start_of_day = current_time - (current_time % 86400)

                                redis_key = f"{request.user_id}:{start_of_day}"

                                current_count = redis_instance.get(redis_key)

                                if current_count is None:
                                    current_count = 0
                                else:
                                    current_count = int(current_count)

                                if current_count >= daily_limit:
                                    return JSONResponse(
                                        content={"message": f"User: {request.user_id} is limited in requests today",
                                                 "status": "ERROR"},
                                        status_code=403)

                                redis_instance.incr(redis_key)
                                redis_instance.expire(redis_key, 86400)

                                server_list = get_server_with_less_queue()
                                if server_list:
                                    response = face_swap_request(server_list, "face_swap/",
                                                                    headers={'accept': 'application/json', 'Content-Type': 'application/json'},
                                                                    json_dict={'typeReq': request.typeReq,
                                                                                'template_id': request.template_id,
                                                                                'faceFrom': request.faceFrom,
                                                                                'faceTo': request.faceTo,
                                                                                'watermark': False,
                                                                                'premium': True,
                                                                                'new':False})
                                    return response
                                
                                else:
                                    error_msg_to_tg(f"Error!\nSomething wrong with queue servers in /face_swap/ - status_code: {500}")
                                    return JSONResponse(content={"message": f"Something wrong with queue servers",
                                                                 "status": "ERROR"},
                                                        status_code=500)
                            else:
                                return JSONResponse(
                                    content={"message": f"User: {request.user_id} subscription is not active",
                                             "status": "ERROR"},
                                    status_code=403)
                            
                        elif subscription['status'] in ['expired']:
                            return JSONResponse(content={"message": f"EXPIRED Subscription of User: {request.user_id}",
                                                         "status": "ERROR"}, status_code=403)
                        
                else:
                    return JSONResponse(content={"message": f"Check subscription of User: {request.user_id}",
                                                 "status": "ERROR"}, status_code=401)
                
            else:
                return JSONResponse(content={"message": f"Check subscription of User (something wrong): {request.user_id}",
                                             "status": "ERROR"}, status_code=400)
    except Exception as error:
        logging.error(f"ERROR: {error}")
        error_msg_to_tg(f"Error!\nRequest: /face_swap/ - with error: {error}")
        return JSONResponse(content={"message": f"Error in processing user request",
                                     "status": "ERROR"}, status_code=500)


@app.get("/face_swap/result")
async def get_face_swap_process_status(request_id: str):
    try:
        server_list = json.loads(os.environ['SERVER_IPS'])

        for server in server_list:
            try:
                response = requests.get(f"{server}face_swap/result?request_id={request_id}",
                                        headers={'accept': 'application/json'})
                logging.info(response.json())
                
                return JSONResponse(content=response.json(), status_code=200)
                
            except Exception as error:
                logging.error(f"ERROR: {error}")
                error_msg_to_tg(f"Error!\nRequest: /face_swap/result/ - server: {server} - with error: {error}")
                continue

    except Exception as error:
        logging.error(f"ERROR: {error}")
        error_msg_to_tg(f"Error!\nRequest: /face_swap/result/ - with error: {error}")
        return JSONResponse(content={"message": f"Error in processing user request",
                                     "status": "ERROR"}, status_code=500)


@app.get("/delete_redis_key", response_model=Status)
async def delete_info_by_redis_key(user_id: str):
    try:
        if user_id == 'all':
            redis_instance.flushall()
            return Status(status="OK")
        else:
            current_time = int(time.time())
            start_of_day = current_time - (current_time % 86400)

            redis_instance.delete(f"{user_id}:{start_of_day}")

            return Status(status="OK")
    except Exception as error:
        logging.error(f"ERROR: {error}")
        return Status(status="ERROR")


@app.post("/template/add/")
async def upload_template(template: TemplateUpload = Depends(TemplateUpload.as_form)):
    try:
        data = dict()

        data['thumb_data'] = await template.thumb.read()
        data['file_data'] = await template.file.read()
        data['preview_data'] = await template.preview_source.read()

        template_responce = await send_templates_on_nodes(template, data)

        if template_responce:
            return template_responce
        else:
            return Status(status="ERROR")

    except Exception as error:
        logging.error(f"ERROR: {error}")
        error_msg_to_tg(f"Error!\nRequest: /template/add - with error: {error}")
        return Status(status="ERROR")



@app.get("/face_get/result")
async def get_face_swap_process_status(template_id: str):
    try:
        server_list = json.loads(os.environ['SERVER_IPS'])

        for server in server_list:
            try:
                response = requests.get(f"{server}face_get/result?template_id={template_id}",
                                        headers={'accept': 'application/json'})
                
                logging.info(response.json())

            except Exception as error:
                logging.error(f"ERROR: {error}")
                error_msg_to_tg(f"Error!\nRequest: /face_get/result/ - server: {server} - with error: {error}")
                continue

            if response:
                responce = response.json()
                return JSONResponse(content=responce, status_code=200)
            

    except Exception as error:
        logging.error(f"ERROR: {error}")
        error_msg_to_tg(f"Error!\nRequest: /face_get/result/ - with error: {error}")
        return JSONResponse(content={"message": f"Error in processing user request",
                                     "status": "ERROR"}, status_code=500)


@app.post("/check/faces/")
async def detect_face(image: DetectFaceUpload=Depends(DetectFaceUpload.as_form)):
    try:
        response = await send_detect_face_on_nodes(image)

        return response

    except Exception as error:
        logging.error(f"ERROR: {error}")
        return Status(status="ERROR")


if __name__ == "__main__":
    uvicorn.run("server:app", host=os.environ['SERVER_IP'], port=int(os.environ['SERVER_PORT']))
