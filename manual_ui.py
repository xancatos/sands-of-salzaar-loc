import pandas as pd
import json

file_path = '../Excel/Localization/english/Y游戏内文字_Strings_UI_hotfix.xlsx'
df = pd.read_excel(file_path)

translations = {
    "当前版本：{0}": "Version: {0}",
    "新游戏": "New Game",
    "读取游戏": "Load Game",
    "设置": "Settings",
    "模组": "Mods",
    "更新日志": "Update Log",
    "更新计划": "Future Plans",
    "制作名单": "Credits",
    "退出": "Exit",
    "向部落与弯刀开发组汇报问题": "Report issues to the Sands of Salzaar development team",
    "BUG类型": "Bug Type",
    "请选择..": "Select...",
    "是否提交存档": "Submit save file?",
    "否": "No",
    "问题描述": "Problem Description",
    "请描述你所遇到的问题，以及复现该问题的步骤。\n\n步骤请按照1、2、3、4操作来，请尽量详细。": "Please describe the issue you encountered and the steps to reproduce it.\n\nPlease list the steps (1, 2, 3...) and be as detailed as possible.",
    "输入你遇到的问题...": "Describe your issue...",
    "游戏截图": "Screenshot",
    "提交": "Submit",
    "通用设置": "General",
    "游戏设置": "Gameplay",
    "快捷键": "Hotkeys",
    "游戏说明": "Help",
    "意见反馈": "Feedback",
    "分辨率": "Resolution",
    "视窗模式": "Windowed Mode",
    "全屏": "Full Screen",
    "画面品质": "Graphics Quality",
    "抗锯齿": "Anti-aliasing",
    "垂直同步": "Vertical Sync",
    "开启": "On",
    "锁定帧率": "Lock Frame Rate",
    "音效音量": "Sound Effects",
    "音乐音量": "Music",
    "场景音量": "Environmental",
    "禅道模式": "Zen Mode",
    "打开": "On",
    "关闭": "Off",
    "游戏界面中隐藏所有非必要的UI面板，只能用快捷键呼出": "Hides all non-essential UI elements; access them only via hotkeys."
}

count = 0
for idx, row in df.iterrows():
    orig = row['VALUE(Origin)']
    if pd.isna(orig): continue
    orig_clean = str(orig).strip()
    
    if orig_clean in translations:
        df.at[idx, 'VALUE'] = translations[orig_clean]
        count += 1

df.to_excel(file_path, index=False)
print(f"Applied {count} translations to UI strings!")
