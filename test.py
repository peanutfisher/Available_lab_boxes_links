from dominate.tags import *
import dominate

cols = ['Array Model', 'SimplifiedSymmwin', 'RemoteAnywhere']
rows = ['PowerMax', 'link1', 'link2']

#print(html(body(h1('hello, World!'))))

h = html()
h.add(head('Available Links of Simplified Symmwin and RemoteAnywhere'))
b = h.add(body(bgcolor='Silver'))
t = b.add(table(border='1', cellspacing='0'))
tb = t.add(tbody())
with tb:
    # the 1st colum
    tr([th(name, width='12%') for name in cols ])
    l = tr(bgcolor='lime')
    with l:
        td(width='12%').add(a('PowerMax'))
        td(width='12%').add(a('link1', href='link1'))
        td(width='12%').add(a('link2', href='link2'))
    
    
print(h)