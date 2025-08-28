import json
import math
import re
import traceback
import requests

from home.lark_client import meta
from util import time_util
from util.log_util import logger


class LarkSpreadSheet:
    def __init__(self, sheet_token, headers=meta.get_headers()):
        self.token = sheet_token
        self.headers = headers

    def get_meta_info(self, retry_max=3):
        url = 'https://your-feishu-instance.com'.format(self.token)
        retry = 0
        while retry < retry_max:
            retry += 1
            resp = requests.get(url, headers=self.headers)
            if resp.ok and resp.json()['code'] == 0:
                return json.loads(resp.text)
            self.headers = meta.get_headers()
        return None

    # 写入下拉,基本格式为[[{"type": "multipleValue", "values": tag_list}]].
    # 注意tag_list必须传入list.逗号分隔的字符串等格式都不行.
    def write(self, loc, values, retry_max=3):
        url = 'https://your-feishu-instance.com'.format(self.token)
        # 自动分批插入，一次4k行最多
        max_row = 4020
        loop = math.ceil(len(values) / max_row)
        begin_row = int(re.sub(r'^[a-zA-Z]*|[a-zA-Z]*$', '', loc.split('!')[-1].split(':')[0]))
        tip = ''
        for i in range(loop):
            each_values = values[i*max_row:(i+1)*max_row]
            each_loc = loc.replace('{}:'.format(begin_row), '{}:'.format(begin_row+i*max_row))
            data = {"valueRange": {"range": each_loc, "values": each_values}}
            retry, ok = 0, False
            while retry < retry_max:
                retry += 1
                resp = requests.put(url, headers=self.headers, data=json.dumps(data))
                logger.info('[lark write spreadsheet] loop: {}/{}, resp: {}'.format(i+1, loop, resp.text))
                if resp.ok and resp.json()['code'] == 0:
                    ok = True
                    break
                else:
                    tip = resp.json().get('msg', '')
            if not ok:
                msg = '[sheet_token] {}\n[loc] {}\n [values] {}'.format(self.token, loc, values)
                logger.error('[lark write sheet failed] ' + msg)
                return False, tip
                # Lark(constant.LARK_CHAT_ID_P0).send_rich_text('lark write sheet failed', msg)
        return True, tip

    def write_append(self, loc, values, retry_max=3):
        url = 'https://your-feishu-instance.com'.format(self.token)
        data = {"valueRange": {"range": loc, "values": values}}
        retry = 0
        while retry < retry_max:
            retry += 1
            resp = requests.post(url, headers=self.headers, data=json.dumps(data))
            if resp.ok and resp.json()['code'] == 0:
                break
            else:
                logger.info('[lark write append] loc: {}, resp: {}'.format(loc, resp.text))
            self.headers = meta.get_headers()
        return True

    def read(self, loc, retry_max=3):
        url = 'https://your-feishu-instance.com'.format(self.token, loc)
        params = {'valueRenderOption': 'UnformattedValue'}
        retry = 0
        while retry < retry_max:
            retry += 1
            resp = requests.get(url, headers=self.headers, params=params)
            data = json.loads(resp.text)
            if resp.ok:
                if data['code'] == 0 and 'data' in data and 'valueRange' in data['data']:
                    return data['data']['valueRange']['values']
            else:
                if data['code'] == 91403:
                    return 'No access to this sheet, pls share with larkbot: Obs'
            self.headers = meta.get_headers()
        return None

    def read_single(self, loc, max_retry=3):
        url = 'https://your-feishu-instance.com'.format(self.token, loc)
        params = {'valueRenderOption': 'UnformattedValue'}
        retry = 0
        while retry < max_retry:
            retry += 1
            resp = requests.get(url, headers=self.headers, params=params)
            if resp.ok:
                resp = json.loads(resp.text)
                if resp['code'] == 0 and 'data' in resp and 'valueRange' in resp['data']:
                    raw = resp['data']['valueRange']['values']
                    result = []
                    if raw:
                        for each in raw:
                            if not each:
                                result.append('')
                            else:
                                result.append(each[0])
                    return result
            else:
                logger.error('[lark read single error] sheet_token: {}, loc: {}, resp: {}'.format(self.token, loc, resp))
            self.headers = meta.get_headers()
        return None

    def get_max_row(self, sheet_id, obj_column='A'):
        resp = self.read(sheet_id+'!{}:{}'.format(obj_column, obj_column))
        if resp is None:
            return None
        return len(resp)

    def write_pic(self, loc, pic_url, proxy=False, retry_max=3):
        retry = 0
        while retry < retry_max:
            retry += 1
            try:
                if pic_url is None or pic_url == '':
                    return None
                url = 'https://your-feishu-instance.com'.format(self.token)
                name = str(pic_url).split('/')[-1].split('?')[0]
                if '.' not in name:
                    name += '.jpeg'
                proxies = {}
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
                }
                print(f'begin pic: {time_util.get_cnt_now()}')
                img_resp = requests.get(pic_url, proxies=proxies, headers=headers)
                print(f'end pic: {time_util.get_cnt_now()}')
                img_bytes = None
                if img_resp.ok and img_resp.content is not None:
                    # with open('./tmp.png', 'wb') as f:
                    #     f.write(img_resp.content)
                    img_bytes = bytearray(img_resp.content)
                    # img = Image.open(BytesIO(response.content))
                    # # 使用save方法将图片保存为PNG格式
                    # img.save(output_path, 'PNG')
                img_array = []
                if img_bytes is not None:
                    for each in img_bytes:
                        img_array.append(each)
                data = {'range': loc, 'image': img_array, 'name': name}
                print(f'begin upload: {time_util.get_cnt_now()}')
                resp = requests.post(url, headers=self.headers, data=json.dumps(data))
                print('lark pic resp: {}'.format(resp.text))
                if resp.ok and resp.json()['code'] == 0:
                    return json.loads(resp.text)
            except Exception:
                print(traceback.format_exc())
            self.headers = meta.get_headers()
        return None

    def set_style(self, loc, font_color='#000000', bold=False, style_info=None):
        url = 'https://your-feishu-instance.com'.format(self.token)
        if not style_info:
            style_info = {'font': {'bold': bold}, 'foreColor': font_color}
        data = {"appendStyle": {"range": loc, "style": style_info}}
        resp = requests.put(url, headers=self.headers, data=json.dumps(data))
        logger.info('[lark style] response: {}'.format(resp.text))
        if resp.ok:
            return json.loads(resp.text)
        return None

    def read_text(self, loc, must_have=''):
        result = []
        resp = self.read(loc)
        for i in range(len(resp)):
            if resp[i] is not None and len(resp[i]) > 0:
                if type(resp[i][0]) == list:
                    for each in resp[i][0]:
                        if 'text' not in each:
                            continue
                        if must_have and must_have not in each['text']:
                            continue
                        text = each['text']
                        result.append(text)
        return result

    def del_rows(self, sheet_id, detect_col='A', start=2, end=None):
        if end is None:
            end = self.get_max_row(sheet_id, obj_column=detect_col)
        if end < start:
            return None
        url = 'https://your-feishu-instance.com'.format(self.token)
        data = {"dimension": {"sheetId": sheet_id, "majorDimension": "ROWS", "startIndex": start, "endIndex": end}}
        resp = requests.delete(url, headers=self.headers, data=json.dumps(data))
        if resp.ok:
            return json.loads(resp.text)
        return None

    # detail body config: https://your-feishu-instance.com
    def operate_sheets(self, requests_body):
        url = 'https://your-feishu-instance.com'.format(self.token)
        data = {'requests': requests_body}
        resp = requests.post(url, headers=self.headers, data=json.dumps(data))
        if resp.ok:
            return json.loads(resp.text)
        else:
            logger.error('[lark operate sheets] resp: {}'.format(resp.text))
        return None

    # detail config: https://your-feishu-instance.com
    def update_dimension(self, data):
        url = 'https://your-feishu-instance.com'.format(self.token)
        resp = requests.put(url, headers=self.headers, data=json.dumps(data))
        if resp.ok:
            return json.loads(resp.text)
        return None

    def decorate_row(self, sheet_id, start, end, height, visible=True):
        body_row = {
            "dimension": {
                "sheetId": sheet_id,
                "majorDimension": "ROWS",
                "startIndex": start,
                "endIndex": end
            },
            "dimensionProperties": {
                "visible": visible,
                "fixedSize": height
            }
        }
        return self.update_dimension(body_row)

    def decorate_column(self, sheet_id, start, end, width, visible=True):
        body_column = {
            "dimension": {
                "sheetId": sheet_id,
                "majorDimension": "COLUMNS",
                "startIndex": start,
                "endIndex": end
            },
            "dimensionProperties": {
                "visible": visible,
                "fixedSize": width
            }
        }
        return self.update_dimension(body_column)

    # config: https://your-feishu-instance.com
    def decorate_cell(self, data):
        url = 'https://your-feishu-instance.com'.format(self.token)
        resp = requests.put(url, headers=self.headers, data=json.dumps(data))
        if resp.ok:
            return json.loads(resp.text)
        return None


    def dye_cell(self, sheet_id, cell, cell_to=None, color='#DFE0E3'):
        if not cell_to:
            cell_to = cell
        cell_decorate = {
            'data': [
                {
                    'ranges': [f'{sheet_id}!{cell}:{cell_to}'],
                    'style': {
                        'backColor': color
                    }
                }
            ]
        }
        return self.decorate_cell(cell_decorate)

    def clear_format(self, loc):
        cell_decorate = {
            'data': [
                {
                    'ranges': [loc],
                    'style': {
                        'clean': True
                    }
                }
            ]
        }
        self.decorate_cell(cell_decorate)

    def move_sheet(self, sheet_id, new_index):
        request_body = [{
          "updateSheet": {
            "properties": {
              "sheetId": sheet_id,
              "index": new_index,
            }
          }
        }]
        self.operate_sheets(request_body)

    def set_dropdown(self, loc, values: [str], multi=False, colors=None, max_retry=3):
        url = 'https://your-feishu-instance.com'.format(self.token)
        # 自动分批插入，一次4k行最多
        max_row = 4020
        begin_row = int(re.sub(r'^[a-zA-Z]*|[a-zA-Z]*$', '', loc.split('!')[-1].split(':')[0]))
        end_row = int(re.sub(r'^[a-zA-Z]*|[a-zA-Z]*$', '', loc.split('!')[-1].split(':')[-1]))
        loop = math.ceil(end_row / max_row)
        col = loc.split('!')[-1].split(':')[-1].replace('{}'.format(end_row), '')
        for i in range(loop):
            each_loc = loc.replace('{}:'.format(begin_row), '{}:'.format(begin_row + i * max_row))
            each_end = min(begin_row + (i+1) * max_row, end_row)
            each_loc = each_loc.replace(':{}{}'.format(col, end_row), ':{}{}'.format(col, each_end))
            data = {'range': each_loc, 'dataValidationType': 'list',
                    'dataValidation': {'conditionValues': values,
                                       'options': {'multipleValues': multi,
                                                   'highlightValidData': True if colors else False,
                                                   'colors': colors}}}
            retry = 0
            while retry < max_retry:
                retry += 1
                resp = requests.post(url, headers=self.headers, data=json.dumps(data))
                logger.info('[lark set dropdown] for loc, resp: {}'.format(resp.text))
                if resp.ok:
                    break
        return None

    def replace_pic(self, sheet_id, column, row_begin, row_end=None):
        if not row_end:
            row_end = ''
        data = self.read_single(f'{sheet_id}!{column}{row_begin}:{column}{row_end}')
        row = row_begin - 1
        for cell in data:
            row += 1
            if type(cell) == list:
                cell = cell[0]
            if not cell:
                continue
            if url := cell.get('text', None):
                self.write_pic(f'{sheet_id}!{column}{row}:{column}{row}', url)


if __name__ == '__main__':
    sheet_token_ = 'XvSDsnUTChEj7lt5YIKcNlUJnxg'
    lss = LarkSpreadSheet(sheet_token_)
    body_ = [{'addSheet': {'properties': {'title': '1-cons', 'index': 0}}},
             {'addSheet': {'properties': {'title': '2-scenario', 'index': 1}}},
             {'addSheet': {'properties': {'title': '3-pros', 'index': 2}}},
             {'deleteSheet': {'sheetId': 'b5e596'}}]
    o = lss.operate_sheets(body_)
    # o = lss.get_meta_info()
    print(o)


