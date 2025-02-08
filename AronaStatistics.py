import pandas as pd

from utils import generate_rich_table

class AronaStatistics:
    """負責讀取 `data.xlsx` 並處理 RAID/ERAID 數據"""

    def __init__(self, file_path="data.xlsx"):
        self.file_path = file_path
        self.xlsx = pd.ExcelFile(file_path)

    def get_raid_name(self, season: int):
        """根據 `data.xlsx` 找出 RAID SXX 的正確名稱"""
        for sheet in self.xlsx.sheet_names:
            df = pd.read_excel(self.xlsx, sheet_name=sheet, nrows=1)
            for column in df.columns:
                if f"S{season}" in column and "總力戰" in column:
                    return column
        print(f"⚠ 未找到 S{season} 相關的 RAID 總力戰", flush=True)
        return f"S{season} 總力戰 (未知名稱)"

    def get_raid_stats(self, season: int, rank: int):
        """獲取 RAID 指定賽季的角色數據"""
        raid_name = self.get_raid_name(season)
        for sheet in self.xlsx.sheet_names:
            df = pd.read_excel(self.xlsx, sheet_name=sheet)
            if raid_name in df.columns:
                return (
                    df[['stdNm', raid_name]]
                    .sort_values(by=raid_name, ascending=False)
                    .dropna()
                    .values.tolist()
                )
        return []

    def get_eraid_name(self, season: int, armor_type: str):
        """
        根據 `data.xlsx` 找出 ERAID SXX 的正確名稱，只匹配指定 `armor_type`
        """
        possible_names = []
        for sheet in self.xlsx.sheet_names:
            df = pd.read_excel(self.xlsx, sheet_name=sheet, nrows=1)
            for column in df.columns:
                if f"S{season}" in column and "大決戰" in column:
                    if armor_type in column:
                        possible_names.append(column)
        if not possible_names:
            print(
                f"⚠ 未找到 S{season} {armor_type} 相關的 ERAID 大決戰", flush=True
            )
            return f"S{season} {armor_type} 大決戰 (未知名稱)"
        if len(possible_names) > 1:
            print(
                f"⚠ 警告: S{season} {armor_type} 匹配到多個結果, 可能有誤: {possible_names}",
                flush=True,
            )
        return possible_names[0]

    def get_eraid_stats(self, season: int, armor_type: str, rank: int):
        """獲取 ERAID 指定賽季、裝甲類型的角色數據"""
        valid_armor_types = ["LightArmor", "ElasticArmor", "HeavyArmor", "Unarmed"]
        if armor_type not in valid_armor_types:
            raise ValueError(
                f"⚠ armor_type 必須是 {valid_armor_types}, 但收到: {armor_type}"
            )

        eraid_name = self.get_eraid_name(season, armor_type)
        for sheet in self.xlsx.sheet_names:
            df = pd.read_excel(self.xlsx, sheet_name=sheet)
            if eraid_name in df.columns:
                return (
                    df[['stdNm', eraid_name]]
                    .sort_values(by=eraid_name, ascending=False)
                    .dropna()
                    .values.tolist()
                )
        return []

    def get_student_stats(self, stu_name: str, seasons: int, armor_type: str):
        """
        獲取 stu_name 在 S{seasons} {armor_type} 大決戰 的數據，
        並回傳格式化表格（非 Markdown 格式）。

        此函式假設從 Excel 擷取到的區塊：
          - 第一列：整個表格的標題（例如 "S13 - 高茲 Outdoor HeavyArmor 大決戰"）
          - 第二列：各欄位表頭（例如 "排名", "借用", "三星以下", ... , "共計"）
          - 後續列：資料內容
        """
        matching_sheets = []
        print(f"🔍 搜尋 `{stu_name}` 相關的工作表...", flush=True)

        for sheet in self.xlsx.sheet_names:
            if stu_name in sheet:
                matching_sheets.append(sheet)
                print(f"✅ 找到 `{stu_name}` 相關的工作表: {sheet}", flush=True)

        if not matching_sheets:
            print(f"❌ 找不到 `{stu_name}` 相關的工作表", flush=True)
            return None, None

        print(
            f"🔍 在 `{stu_name}` 的工作表內，搜尋 `S{seasons}`, `{armor_type}`, `大決戰` 是否出現在內容中...",
            flush=True,
        )

        for sheet in matching_sheets:
            df_full = pd.read_excel(self.xlsx, sheet_name=sheet, header=None)

            found_row = None
            end_row = None
            for index, row in df_full.iterrows():
                row_str = " ".join(row.dropna().astype(str))
                if f"S{seasons}" in row_str and armor_type in row_str and "大決戰" in row_str:
                    found_row = index
                    print(
                        f"🎯 `{sheet}` 內部找到 `S{seasons} {armor_type} 大決戰` (位於第 {found_row+1} 行)",
                        flush=True,
                    )
                    continue

                if found_row is not None and "S" in row_str and "大決戰" in row_str:
                    end_row = index
                    print(
                        f"⏹ 截斷 `S{seasons} {armor_type} 大決戰` 數據 (結束於第 {end_row+1} 行)",
                        flush=True,
                    )
                    break

            if found_row is not None:
                # 擷取 DataFrame 區間
                if end_row is not None:
                    df_section = df_full.iloc[found_row:end_row].reset_index(drop=True)
                else:
                    df_section = df_full.iloc[found_row:].reset_index(drop=True)

                # 清理 NaN 值
                df_section = (
                    df_section.dropna(how="all", axis=1)
                    .dropna(how="all", axis=0)
                    .astype(str)
                )

                # 假設第一列為標題，第二列為欄位名稱，後續為資料內容
                title = df_section.iloc[0, 0].strip()
                headers = [str(x).strip() for x in df_section.iloc[1]]
                data_rows = df_section.iloc[2:].values.tolist()

                # 利用 rich 產生表格字串
                stats_text = generate_rich_table(title, headers, data_rows)

                print("✅ 成功生成表格，準備發送 Discord 訊息！", flush=True)
                return sheet, stats_text

        print(
            f"❌ `{stu_name}` 的 S{seasons} {armor_type} 大決戰 沒有在內容中找到",
            flush=True,
        )
        return None, None
    
    