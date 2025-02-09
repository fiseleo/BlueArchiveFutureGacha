import discord
from discord import app_commands
from discord.ext import commands
from AronaStatistics import AronaStatistics
import os
import sys
import asyncio
from utils import text_to_image
import subprocess


# 設定 Bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# 確保 `data.xlsx` 存在
if not os.path.exists("data.xlsx"):
    print("❌ 錯誤：找不到 `data.xlsx`，請確認檔案已生成！")
    exit(1)

# 讀取 Excel
arona_stats = AronaStatistics("data.xlsx")

@bot.event
async def on_ready():
    print(f'✅ 已登入：{bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"🔄 成功同步 {len(synced)} 個應用程式指令")
    except Exception as e:
        print(f"❌ 同步指令失敗: {e}")

def get_rank_range_str(rank: int) -> str:
    """
    根據 rank 回傳對應的區間文字：
      - 1 ~ 1000：返回 "排名 1~1000 內"
      - 1001 ~ 5000：返回 "排名 1001~5000 內"
      - 5001 ~ 10000：返回 "排名 5001~10000 內"
      - 10001 ~ 20000：返回 "排名 10001~20000 內"
    如果 rank 不在這些範圍內，則拋出錯誤。
    """
    if 1 <= rank <= 1000:
        return "排名 1~1000 內"
    elif 1001 <= rank <= 5000:
        return "排名 1001~5000 內"
    elif 5001 <= rank <= 10000:
        return "排名 5001~10000 內"
    elif 10001 <= rank <= 20000:
        return "排名 10001~20000 內"
    else:
        raise ValueError(f"⚠ Rank {rank} 不在支援的範圍內")

@bot.tree.command(name="raid_stats", description="取得 總力戰 角色使用統計")
async def raid_stats(interaction: discord.Interaction, season: int, rank: int):
    await interaction.response.defer()

    raid_name = arona_stats.get_raid_name(season)  # 取得 RAID SXX 的名稱
    data = arona_stats.get_raid_stats(season, rank)

    if not data:
        await interaction.followup.send(f"⚠ 無法取得 `{raid_name}` {get_rank_range_str(rank)} 的數據")
        return

    # 使用輔助函數 get_rank_range_str 來顯示 rank 區間
    embed = discord.Embed(
        title=f"📊 {raid_name} {get_rank_range_str(rank)} 角色使用率", 
        color=discord.Color.blue()
    )
    for name, count in data[:10]:
        embed.add_field(name=name, value=f"使用次數: `{count}`", inline=False)

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="eraid_stats", description="取得 大決戰 角色使用統計")
@app_commands.choices(armor_type=[
    app_commands.Choice(name="LightArmor", value="LightArmor"),
    app_commands.Choice(name="ElasticArmor", value="ElasticArmor"),
    app_commands.Choice(name="HeavyArmor", value="HeavyArmor"),
    app_commands.Choice(name="Unarmed", value="Unarmed")
])
async def eraid_stats(interaction: discord.Interaction, season: int, armor_type: str, rank: int):
    await interaction.response.defer()

    eraid_name = arona_stats.get_eraid_name(season, armor_type)  # 取得 ERAID SXX 的名稱

    try:
        data = arona_stats.get_eraid_stats(season, armor_type, rank)
    except ValueError as e:
        await interaction.followup.send(str(e))
        return

    if not data:
        await interaction.followup.send(f"⚠ 該季 {season} {armor_type} 類型的角色數據不存在！")
        return

    # 修正 Embed 標題，確保 armor_type 只顯示一次，並加入 rank 區間文字
    embed = discord.Embed(
        title=f"📊 大決戰 {eraid_name} {get_rank_range_str(rank)} 角色使用率", 
        color=discord.Color.green()
    )
    for name, count in data[:10]:
        embed.add_field(name=name, value=f"使用次數: {count}", inline=False)

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="eraid_stats_stu", description="取得特定角色的大決戰數據")
@app_commands.choices(armor_type=[
    app_commands.Choice(name="LightArmor", value="LightArmor"),
    app_commands.Choice(name="ElasticArmor", value="ElasticArmor"),
    app_commands.Choice(name="HeavyArmor", value="HeavyArmor"),
    app_commands.Choice(name="Unarmed", value="Unarmed")
])
async def statstu(interaction: discord.Interaction, stu_name: str, seasons: int, armor_type: str):
    await interaction.response.defer()

    # 呼叫 AronaStatistics 的方法
    sheet_name, stats_text = arona_stats.get_student_stats(stu_name, seasons, armor_type)
    if stats_text is None:
        await interaction.followup.send(f"⚠ 找不到 `{stu_name}` `S{seasons}` `{armor_type}` `大決戰` 的數據")
        return

    # Debug 印出表格文字
    print("【Debug】最終表格文字內容：\n", stats_text)

    # 轉換文字為圖片
    image_bytes = text_to_image(stats_text, font_path="SarasaFixedCL-ExtraLight.ttf", font_size=42)

    # **建立 Discord Embed**
    embed = discord.Embed(
        title=f"📊 {stu_name} - {sheet_name} 的使用數據",
        description="請參考下方表格圖片：",
        color=discord.Color.purple()
    )

    # **將圖片附加到 Embed**
    embed.set_image(url="attachment://table.png")

    # **發送 Embed 與圖片**
    await interaction.followup.send(
        embed=embed,
        file=discord.File(image_bytes, filename="table.png")
    )

@bot.tree.command(name="raid_stats_stu", description="取得特定角色的總力戰數據")

async def statstu(interaction: discord.Interaction, stu_name: str, seasons: int):
    await interaction.response.defer()

    # 呼叫 AronaStatistics 的方法
    sheet_name, stats_text = arona_stats.get_student_stats_raid(stu_name, seasons)
    if stats_text is None:
        await interaction.followup.send(f"⚠ 找不到 `{stu_name}` `S{seasons}` `總力戰` 的數據")
        return

    # Debug 印出表格文字
    print("【Debug】最終表格文字內容：\n", stats_text)

    # 轉換文字為圖片
    image_bytes = text_to_image(stats_text, font_path="SarasaFixedCL-ExtraLight.ttf", font_size=42)

    # **建立 Discord Embed**
    embed = discord.Embed(
        title=f"📊 {stu_name} - {sheet_name} 的使用數據",
        description="請參考下方表格圖片：",
        color=discord.Color.purple()
    )

    # **將圖片附加到 Embed**
    embed.set_image(url="attachment://table.png")

    # **發送 Embed 與圖片**
    await interaction.followup.send(
        embed=embed,
        file=discord.File(image_bytes, filename="table.png")
    )


@bot.tree.command(name="restart", description="🔄 重新啟動 Bot (限管理員)")
@app_commands.checks.has_permissions(administrator=True)
async def restart(interaction: discord.Interaction):
    """重新啟動 Bot"""
    await interaction.response.send_message("🔄 Bot 正在重啟...", ephemeral=True)
    # 給 Discord 一點時間發送訊息
    await asyncio.sleep(2)

    # 重新啟動 Python 程式
    python = sys.executable
    os.execl(python, python, *sys.argv)

@bot.tree.command(name="exec", description="執行 Arona AI Helper（只有作者能用）")
async def exec_script(interaction: discord.Interaction):
    """執行本地 `arona_ai_helper.py`，並在結束後重啟 Bot"""
    await interaction.response.defer(ephemeral=True)  # 🔹 **輸出只有發送者可見**

    # **權限檢查：只有 Bot 擁有者能執行**
    if interaction.user.id != OWNER_ID:
        await interaction.followup.send("⚠ 你沒有權限執行此命令！")
        return

    # **指定 `arona_ai_helper.py` 路徑**
    script_path = os.path.join(os.getcwd(), "arona_ai_helper.py")
    if not os.path.exists(script_path):
        await interaction.followup.send("❌ 找不到 `arona_ai_helper.py`，請確認檔案是否存在。")
        return

    try:
        # **使用 subprocess.Popen 來執行腳本，沒有超時限制**
        process = subprocess.Popen(["python", script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # **等待腳本執行結束**
        stdout, stderr = process.communicate()

        # **合併標準輸出與錯誤輸出**
        output = (stdout + "\n" + stderr).strip()

        if not output:
            output = "✅ 腳本執行成功，但沒有輸出。"

        # **限制輸出長度（避免過長）**
        if len(output) > 1900:
            output = output[:1900] + "\n...(輸出過長，已截斷)"

        # **回傳執行結果**
        embed = discord.Embed(title=f"🖥 執行 `arona_ai_helper.py` 結果", description=f"```\n{output}\n```", color=discord.Color.blue())
        await interaction.followup.send(embed=embed)

        # **通知使用者 bot 即將重啟**
        await interaction.followup.send("🔄 **Arona AI Helper 執行完畢，正在重新啟動 Bot...**")

        # **重啟 bot**
        restart_bot()

    except Exception as e:
        await interaction.followup.send(f"❌ 腳本執行失敗：{e}")

def restart_bot():
    """使用 `execv` 重新啟動 Bot"""
    python = sys.executable
    os.execl(python, python, *sys.argv)  # 🚀 **直接重新啟動當前腳本**

# 讀取 Bot Token
try:
    with open("TOKEN.txt", "r") as token_file:
        TOKEN = token_file.read().strip()
except FileNotFoundError:
    print("❌ 錯誤：找不到 `TOKEN.txt`，請確認 Token 文件存在！")
    exit(1)
try:
    with open("OWNER_ID.txt", "r") as owner_file:
        OWNER_ID = int(owner_file.read().strip())
except FileNotFoundError:
    print("❌ 錯誤：找不到 `OWNER_ID.txt`，請確認擁有者 ID 文件存在！")
    exit(1)

async def main():
    async with bot:
        await bot.start(TOKEN)

import asyncio
asyncio.run(main())
