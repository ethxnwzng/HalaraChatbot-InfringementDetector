import requests

from util.log_util import logger


def get_tone_ads_goods_info():
    ads_goods = ['21B11AT061', '22M14DS076', '22N14TT410', '22D11AT462', '22B11AT290', 'FF0015', '22B11LG285', '22S11AT339', 'FSLS2082L', 'AP20210', 'ML052401', '21B11DS087', '22Q11DD108', '23J14AT599', 'FF0008', '22S14LG352', 'K908', '21Q11LG001', '23J11SH647', '22D14DS487', '23J11AT597', '22D11AT495', '23J14AT612', '22B11SK304', '1837', 'HB0192', '22L15PN001', 'SX050503ktj', '22M14DS007', '22W14SH003', '02414']
    head = 'Below are our Halara product data(each product has: [Product Code]/[Product Name]/[Category]/[Price]/[Material]/[Features]):'
    tail = '----product data end----'
    prompt = head + '\n\n'
    for i in range(len(ads_goods)):
        if i >= 1:
            break
        code = ads_goods[i]
        url = 'https://your-domain.com'.format(code)
        logger.info('[fetch goods detail]: {}. {}'.format(i+1, code))
        resp = requests.get(url)
        if resp and resp.json():
            resp = resp.json()['data']
            name = resp['title']
            category = '/'.join([resp['category1'], resp['category2'], resp['category3'], resp['category4']])
            price = str(resp['price']) + resp['price_unit']
            material = '\n'.join(resp['materials'])
            features = resp['features']
            if len(features) == 0:
                logger.error('empty features for {}'.format(code))
                break
            prompt += '[Product Code]\n{}\n'.format(code)
            prompt += '[Product Name]\n{}\n'.format(name)
            prompt += '[Category]\n{}\n'.format(category)
            prompt += '[Price]\n{}\n'.format(price)
            prompt += '[Material]\n{}\n'.format(material)
            prompt += '[Features]\n'
            for k in range(len(features)):
                prompt += '{}. {}\n'.format(k+1, features[k])
            prompt += '\n'
    prompt += tail
    return prompt


if __name__ == '__main__':
    o = get_tone_ads_goods_info()
    print(o)

