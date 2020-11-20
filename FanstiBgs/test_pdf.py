# -*- coding: utf-8 -*-
import pdfkit, imgkit

body = """
<html>
  <head>
  </head>
  Hello World!
</html>
"""
# path_wkhtmltopdf = r'D:\\wkhtmltopdf\\bin\\wkhtmltopdf.exe'
path_wkhtmltopdf_image = r'D:\\wkhtmltopdf\\bin\\wkhtmltoimage.exe'
# config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
config_img = imgkit.config(wkhtmltoimage=path_wkhtmltopdf_image)
imgkit.from_string(body, output_path=r'D:\\auto.png', config=config_img)
# pdfkit.from_string(body, r'D:\\test.pdf', configuration=config)