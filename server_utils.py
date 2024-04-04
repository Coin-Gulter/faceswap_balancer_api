import os
import json
import logging
import requests
import traceback
from dotenv import load_dotenv
from requests import Response
from requests_toolbelt.multipart.encoder import MultipartEncoder

from schemas import TemplateUpload, DetectFaceUpload

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def error_msg_to_tg(text):
    try:
        requests.get(f"https://api.telegram.org/bot{os.environ['BOT_TOKEN']}/sendMessage",
                     data={"chat_id": os.environ['CHAT_ID'],
                           "text": text})
    except Exception as ex:
        logging.error(f"ERROR: Send to bot {ex}")


def face_swap_request(server_list, endpoint, headers, json_dict) -> Response:
    for server in server_list:
        try:
            logging.info(f"server: {server}")
            response = requests.post(f"{server}{endpoint}", headers=headers, json=json_dict)
        except Exception as error:
            logging.error(f"ERROR: {error}")
            error_msg_to_tg(f"Error!\nRequest: /face_swap/ - server: {server} - with error: {error}")
        else:
            return response.json()


def get_server_with_less_queue() -> list | None:
    try:
        server_list = json.loads(os.environ['SERVER_IPS'])
        logging.info(f"Servers list {server_list}")
        server_dict = {}

        for server in server_list:
            try:
                response = requests.get(f"{server}queue_status/swapface")
                logging.info(f"Resp Serv Q {response} Server: {server}")
                if response.status_code == 200:
                    server_dict[server] = response.json()
                elif response.status_code == 500:
                    logging.error(f"Server returned status code 500. Server: {server}")
                    error_msg_to_tg(f"Error!\nRequest: /queue_status/swapface/ - server: {server} - with error: {error}")
                    server_dict[server] = response.json()
                    continue
                else:
                    logging.warning(f"Unexpected status code {response.status_code}. Server: {server}")
                    error_msg_to_tg(f"Error!\nRequest: /queue_status/swapface/ - server: {server} - unexpected status code with error: {error}")
                    continue
            except Exception as error:
                logging.error(f"ERROR: Send request queue_status: {error} Server: {server}")
                error_msg_to_tg(f"Error!\nRequest: /queue_status/swapface/ - server: {server} - with error: {error}")
                continue
            
        try:
            for key, value in server_dict.items():
                server_dict[key] = value.get('message_count', 0)

            server_dict = dict(sorted(server_dict.items(), key=lambda item: item[1]))
                    
        except Exception as ex:
            tb = traceback.TracebackException.from_exception(ex, capture_locals=True)
            logging.error(f"ERROR: Filter servers: {tb} | {ex}")
            error_msg_to_tg(f"Error!\nRequest: /queue_status/swapface/ - with error: {ex}")

        if server_dict:
            return server_dict

        logging.error(f"ERROR: empty server list")
    except Exception as error:
        tb = traceback.TracebackException.from_exception(error, capture_locals=True)
        logging.error(f"ERROR: Get servers: {error} | {tb}")
        error_msg_to_tg(f"Error!\nRequest: /queue_status/swapface/ - with error: {error}")
        return None


async def send_templates_on_nodes(template: TemplateUpload, data: dict):
    try:
        server_list = json.loads(os.environ['SERVER_IPS'])
        for server in server_list:
            try:
                categories = template.categories
                premium = '0' if template.premium == "0" else '1'

                multipart_data = MultipartEncoder(
                            fields={
                                # plain text fields
                                'premium': premium,
                                'categories': categories,

                                # file upload field
                                'thumb': (template.thumb.filename, data['thumb_data'], template.thumb.content_type),
                                'file': (template.file.filename, data['file_data'], template.file.content_type),
                                'preview_source': (template.preview_source.filename, data['preview_data'], template.preview_source.content_type)
                            }
                        )

                response = requests.post(f"{server}template/add/",
                                        data=multipart_data,
                                        headers={'Content-Type': multipart_data.content_type},
                                        timeout = 30)
                
            except Exception as error:
                logging.error(f"ERROR: {error}")
                error_msg_to_tg(f"Error!\nRequest: /template/add/ - server: {server} - with error: {error}")
                continue

            if response:
                response = response.json()
                break
            else:
                response = {"status": "Error", "request_id": ''}
                
        return response
    
    except Exception as error:
        logging.error(f"ERROR: {error}")
        error_msg_to_tg(f"Error!\nRequest: /template/add/ - with error: {error}")
        return False


async def send_detect_face_on_nodes(image:DetectFaceUpload):
    try:
        server_list = json.loads(os.environ['SERVER_IPS'])

        for server in server_list:
            try:
                response = requests.post(f"{server}check/faces", headers={'accept': 'application/json'},
                                         json=image.image)
            except Exception as error:
                logging.error(f"ERROR: {error}")
                response = {
                                    "error":str(error)
                                    }
                error_msg_to_tg(f"Error!\nRequest: /check/faces/ - server: {server} - with error: {error}")
                continue
            else:
                logging.info(response)
                response = response.json()
                break

        return response
    except Exception as error:
        logging.error(f"ERROR: {error}")
        error_msg_to_tg(f"Error!\nRequest: /check/faces/ - with error: {error}")
        return False



# def connect_to_db():
#     try:
#         # Connect to the database
#         connection = pymysql.connect(host=os.environ['DB_HOST'],
#                                      user=os.environ['DB_USERNAME'],
#                                      password=os.environ['DB_PASSWORD'],
#                                      database=os.environ['DB_NAME'],
#                                      cursorclass=pymysql.cursors.Cursor,
#                                      ssl_ca=os.environ['DB_SSL'],
#                                      autocommit=True)
#         return connection
#     except pymysql.MySQLError as e:
#         logging.error(f"Error connecting to MySQL {e}")
#         print(f"Error connecting to MySQL: {e}")
#         return None

# async def setUseridDB(reqId, userId):
#     print(f"TaskID: {reqId}")
#     print(f"UserID: {userId}")
#     try:
#         connection = connect_to_db()
#         with connection.cursor() as cursor:
#             table = os.environ['TASK_TABLE_NAME_1']
#             sql_query = f"UPDATE {table} SET user_id = %s WHERE task_id = %s"
#             cursor.execute(sql_query, (userId, reqId))
#         connection.commit()
#     except pymysql.Error as e:
#         logging.error(f"Error MySQL {e}")
#         print(f"Error MySQL: {e}")
        
#     finally:
#         connection.close()
    

# async def send_categories_on_nodes(category: CategoryUpload):
#     try:
#         server_list = json.loads(os.environ['SERVER_IPS'])

#         for server in server_list:
#             try:
#                 response = requests.post(f"{server}categories/add/",
#                                          headers={'accept': 'application/json'},
#                                          json={'title': category.title})
#             except Exception as error:
#                 logging.error(f"ERROR: {error}")
#                 # error_msg_to_tg(f"Error!\nServer: {server}")
#                 continue

#             if response.status_code != 200:
#                 return False

#         return True
#     except Exception as error:
#         logging.error(f"ERROR: {error}")
#         return False


# async def update_categories_on_nodes(category: CategoryUpdate):
#     try:
#         server_list = json.loads(os.environ['SERVER_IPS'])
#         for server in server_list:
#             try:
#                 response = requests.patch(f"{server}categories/update/",
#                                           headers={'accept': 'application/json'},
#                                           json={'id': category.id,
#                                                 'title': category.title})
#             except Exception as error:
#                 logging.error(f"ERROR: {error}")
#                 # error_msg_to_tg(f"Error!\nServer: {server}")
#                 continue

#             if response.status_code != 200:
#                 return False
#             return True
#     except Exception as error:
#         logging.error(f"ERROR: {error}")
#         return False
    

# def face_swap_custom_request(server_list, endpoint, headers, json_dict, files) -> Response:
#     for server in server_list:
#         try:
#             logging.info(f"server: {server}")
#             response = requests.post(f"{server}{endpoint}", headers=headers,
#                                      data=json_dict, files=files)
#         except Exception as error:
#             logging.error(f"ERROR: {error}")
#             error_msg_to_tg(f"Error!\nServer: {server}")
#         else:
#             return response
