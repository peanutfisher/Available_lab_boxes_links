'''
Author: peanutfisher meifajia@outlook.com
Date: 2024-05-19 17:29:05
LastEditors: peanutfisher meifajia@outlook.com
LastEditTime: 2024-09-20 10:09:10
FilePath: \AvailableLabBox\test.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('my.log', 'w')

console_handler = logging.StreamHandler()

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger.addHandler(file_handler)
logger.addHandler(console_handler)

file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)


logger.debug('this is debug information')
logger.info('this is info information')
logger.warning('this is warning information')
logger.error('this is error information')
logger.critical('this is critical information')