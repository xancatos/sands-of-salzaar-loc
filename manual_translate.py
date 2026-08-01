import pandas as pd

file_path = '../Excel/Localization/english/B兵种单位表_Fighters_hotfix.xlsx'
df = pd.read_excel(file_path)

translations = {
    "入门拳手": "Novice Pugilist",
    "进阶拳手": "Adept Pugilist",
    "职业拳手": "Expert Pugilist",
    "搏击大师": "Master Pugilist",
    "萌新": "Greenhorn",
    "爱好者": "Amateur",
    "高端玩家": "Elite",
    "大佬": "Grandmaster",
    "教练": "Instructor"
}

def translate_row(row):
    orig = row['显示名称_UnitName(Origin)']
    if pd.isna(orig):
        return row['显示名称_UnitName']
    
    # Strip any potential whitespace
    orig_clean = str(orig).strip()
    return translations.get(orig_clean, orig)

df['显示名称_UnitName'] = df.apply(translate_row, axis=1)
df.to_excel(file_path, index=False)
print("Fighters translation applied successfully!")
