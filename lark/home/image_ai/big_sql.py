

SQL_GOODS_MALL_PIC_ALL_ONLINE = """
SELECT gpspu.area_id,
       gpspu.product_spu_id,
       gpspu.selection_spu_id,
       gpspu.supplier_styles_code,
       gpskc.product_skc_id,
       gpskc.selection_skc_id,
       sei.url,
       sei.position
FROM goods_product_skc_ext_image sei
LEFT JOIN goods_product_skc gpskc ON sei.product_skc_id = gpskc.product_skc_id
LEFT JOIN goods_product_spu gpspu ON gpskc.product_spu_id = gpspu.product_spu_id
WHERE sei.status = 2
  AND gpspu.area_id = 10
  AND gpskc.deleted = 2
  AND gpspu.deleted = 2
  AND gpspu.supplier_styles_code = :style_code
ORDER BY gpspu.product_spu_id ASC,
         gpskc.product_skc_id ASC,
         gpskc.position ASC
"""

