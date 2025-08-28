from django.http import JsonResponse


class Response:
    def __init__(self):
        self.code = 0
        self.msg = ''
        self.data = {}


def wrap_ok_response(data):
    resp = Response()
    resp.data = data
    return JsonResponse(resp.__dict__)


def wrap_err_response(code, msg):
    resp = Response()
    resp.code = code
    resp.msg = msg
    return JsonResponse(resp.__dict__)


def get_json_headers():
    return {'Content-Type': 'application/json; charset=utf-8'}

