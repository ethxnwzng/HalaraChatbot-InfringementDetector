import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lark.settings')
import django
django.setup()
from django.db import close_old_connections
from home.image_ai import big_sql
from home.image_ai.models import GoodsProductSpu
from lark.settings import DB_LINK_GOODS_CENTER
from util import time_util
from util.log_util import logger
from sqlalchemy import text, create_engine
from . import big_sql
from .search import get_public_url_from_s3_url

engine_goods = create_engine(DB_LINK_GOODS_CENTER)

def get_goods_mall_all_picture(style_code):
    map_skc_pics = {}
    if not style_code:
        return None
    try:
        sql_ = big_sql.SQL_GOODS_MALL_PIC_ALL_ONLINE
        with engine_goods.connect() as connection:
            records = connection.execute(text(sql_), {"style_code": style_code})
            for each in records:
                # Access by tuple index: (area_id, product_spu_id, selection_spu_id, supplier_styles_code, product_skc_id, selection_skc_id, url, position)
                skc_id = str(each[5])  # selection_skc_id is at index 5
                url = str(each[6])     # url is at index 6
                position = int(each[7]) # position is at index 7
                
                # Convert S3 URL to public URL if it's an S3 URL
                if url.startswith('s3://'):
                    public_url = get_public_url_from_s3_url(url)
                    if public_url:
                        url = public_url
                
                if skc_id not in map_skc_pics:
                    map_skc_pics[skc_id] = []
                map_skc_pics[skc_id].append({'url': url, 'position': position})
            # sort
            for k in map_skc_pics.keys():
                map_skc_pics[k].sort(key=lambda x: x['position'])
            return map_skc_pics
    except Exception as e:
        print(f"Error in get_goods_mall_all_picture: {e}")
        return None


# '2025-07-10', '2025-07-11', datetime
def get_goods(online_from, online_to):
    close_old_connections()
    goods_list = []
    goods_db = GoodsProductSpu.objects.using('goods_center').filter(release_online_at__gte=online_from,
                                                                    release_online_at__lt=online_to,
                                                                    release_online_push_status=2,
                                                                    area_id=10, deleted=2).all().order_by('release_online_at')
    if not goods_db:
        return goods_list
    # deduplicate
    style_tag_set = set()
    for each in goods_db:
        if each.supplier_styles_code in style_tag_set:
            logger.info('style code {} is in tag set'.format(each.supplier_styles_code))
            continue
        style_code = each.supplier_styles_code
        title = each.release_title
        product_spu_id = each.product_spu_id
        global_mall_url = 'https://thehalara.com/products/{}'.format(product_spu_id)
        online_time = each.release_first_online_at.strftime(time_util.TIME_FORMAT_DEFAULT)
        goods_list.append({
            'style_code': style_code,
            'title': title,
            'product_spu_id': product_spu_id,
            'global_mall_url': global_mall_url,
            'online_time': online_time,
        })
    return goods_list


if __name__ == '__main__':
    goods_ = get_goods('2025-07-10', '2025-07-11')
    for each in goods_:
        print(each['style_code'])
        o = get_goods_mall_all_picture(each['style_code'])
        print(o)
        

