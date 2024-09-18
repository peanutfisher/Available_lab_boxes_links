'''
Author: peanutfisher meifajia@outlook.com
Date: 2024-09-12 16:06:16
LastEditors: peanutfisher meifajia@outlook.com
LastEditTime: 2024-09-18 12:38:37
FilePath: \AvailableLabBox\func_test.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''

from jinja2 import Environment, FileSystemLoader
import re
import os.path

# example list
SS_list = ['http://197900830M1.storage.lab.emc.com:8888/toolbox/#/app?userName=AwBOE0G1iO04&password=1nternal', 'http://196800748M1.storage.lab.emc.com:8888/toolbox/#/app?userName=AwBOE0G1iO04&password=1nternal', 'http://120200705M1.storage.lab.emc.com:8888/toolbox/#/app?userName=AwBOE0G1iO04&password=1nternal']
RA_list = ['https://120200705M1.storage.lab.emc.com:9519/login:AwBOE0G1iO04:1nternal:SLC/remctrl_menu.html','https://120200830M1.storage.lab.emc.com:9519/login:AwBOE0G1iO04:1nternal:SLC/remctrl_menu.html', 'https://297700494M1.storage.lab.emc.com:9519/login:AwBOE0G1iO04:1nternal:SLC/remctrl_menu.html']

# defining the TYPE based on SN key num
SN_dict = {'202':'PMAX8500', '200':'PMAX2500', '976':'PMAX8000','979':'PMAX2000', '978':'VMAX250F', '977':'VMAX950F','975':'VMAX850F', '970':'VMAX450F', '972':'VMAX400K','967':'VMAX200K', '968':'VMAX100K'}

SS_patern = ':8888'
#RA_patern = ':9519'

# Dealing with url list to become format[{'TYPE':'XX'},{'SN':'XX'}, {'link':'XX'}...]
def url_to_dict(list1, list2=None):
    """ Convert the list to the dict inside a list so that jinja2 template.html can deal with """
    # target url list
    url_list = []
    
    # dealing with each url
    for url in list1:
        # store the new dict value
        url_dict = {}
        # get each SN pattern from list and do RE search
        for sn in SN_dict.keys():
            p = re.compile('\d'+ sn + '\d+M\d')
            #print(p)
            result = p.search(url)
            # if result found then create the dict and stop this tier for loop
            if result:
                url_dict['TYPE'] = SN_dict[sn]
                SN_name = result.group()
                
                # set a flag for jump out for loop if we found entry in both SS_list and RA_list
                jump = False
                
                # Check if list2 available, if yes then search this list for same SN link
                if list2:
                    
                    # traverse the other list either SS_list or RA_list
                    for link in list2:
                        # If found the same SN in the other list
                        if SN_name in link:
                            #print(link)
                            # check which type of the link is
                            if SS_patern in url:
                                
                                url_dict['SN_SS'] = SN_name
                                url_dict['LINK_SS'] = url
                                url_dict['SN_RA'] = SN_name
                                url_dict['LINK_RA'] = link
                             
                            else:
                                url_dict['SN_RA'] = SN_name
                                url_dict['LINK_RA'] = url
                                url_dict['SN_SS'] = SN_name
                                url_dict['LINK_SS'] = link
                            # deleting the dup one from the list
                            list2.pop(list2.index(link))
                            # jump out the loop as dup one found
                            jump = True
                            # break out as no need to check next one when we have found one dup
                            break
                # If we did not find any dup
                if not jump:
                # check which type of the link is
                    if SS_patern in url:
                        url_dict['SN_SS'] = SN_name
                        url_dict['LINK_SS'] = url
                        url_dict['SN_RA'] = ''
                        url_dict['LINK_RA'] = ''
                    else:
                        url_dict['SN_RA'] = SN_name
                        url_dict['LINK_RA'] = url
                        url_dict['SN_SS'] = ''
                        url_dict['LINK_SS'] = ''        
                            
                # no need to do next SN check as already found one
                break
        # appending each result(if not null) to the new url list
        if not url_dict:
            url_list.append(url_dict) 
     
    return url_list      




def html_table(data):
    # The template location
    file_loader = FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates'))

    # create env
    env = Environment(loader = file_loader)

    # loading template
    template = env.get_template('template.html')

    # render the template
    output = template.render(url_list=data)

    # Write html file
    with open('Available_Lab_boxes.html', 'w') as f:
        f.write(output)

if __name__ == '__main__':
    url_list = url_to_dict(SS_list, RA_list) + url_to_dict(RA_list)
    html_table(url_list)