import PySimpleGUI as sg

# 定义布局
layout = [
    [sg.Frame('组 1', [[sg.Text('这是组 1 中的Text控件')], [sg.Button('组 1 的按钮')]]),
     sg.Frame('组 2', [[sg.Text('这是组 2 中的Text控件')], [sg.Button('组 2 的按钮')]])]
]

# 创建窗口
window = sg.Window('使用Frame分组控件示例', layout)

# 事件循环
while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED:
        break

window.close()