# Write by GPT & Xiang
import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord import ButtonStyle, Embed, Interaction
from discord.ui import Button, View, Select,button,Modal,TextInput
from datetime import datetime,timedelta
import random
import json
import os
import asyncio
import shutil
import math

# 假设这是你的管理者名單
ADMIN_USER_IDS = [584371520395149312] 


# 定義天氣效果
WEATHER_EFFECTS = {
    "晴天": 1.0,  # 分數增減幅度正常
    "暴風雨": 1.5,  # 分數增減幅度增加
    "微風": 0.8,  # 分數增減幅度減少
    "雷電": 2.0,  # 分數增減幅度大幅增加
    "霧霾": random.uniform(0.5, 1.5)  # 分數增減幅度隨機波動
}

# 定義道具
ITEMS = {
    "能量飲料(2金幣)-該場比賽分數浮動增加20%": {
        "price": 2,  # 價格
        "effect": "increase_score_multiplier",  # 效果：增加分數增減幅度
        "value": 1.2  # 分數增減幅度增加 20%
    },
    "鎮定劑(2金幣)-該場比賽分數浮動減少20%": {
        "price": 2,
        "effect": "decrease_score_multiplier",  # 效果：減少分數增減幅度
        "value": 0.8  # 分數增減幅度減少 20%
    },
    "搗蛋卡(5金幣)-該場比賽有機會反轉分數增減效果": {
        "price": 5,
        "effect": "reverse_score",  # 效果：有機會反轉分數增減效果
        "value": -1  # 分數增減效果反轉
    },
    "雙倍卡(4金幣)-該場比賽分數增減雙倍": {
        "price": 4,
        "effect": "double_score",  # 效果：分數增減效果加倍
        "value": 2  # 分數增減效果加倍
    },
    "保護罩(1金幣)-該場比賽分數不受天氣效果影響": {
        "price": 1,
        "effect": "ignore_weather",  # 效果：不受天氣效果影響
        "value": 1  # 不受天氣效果影響
    }
}

# 設定 Bot 物件
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# 地圖池文件名
MAP_POOL_FILE = 'map_pools.txt'
# 玩家數據文件名
PLAYERS_FILE = 'players.txt'

ALLOWED_CHANNEL_ID = 1329473265831514163  # 替換為實際的頻道ID
def backup_data():
    # 定義要備份的檔案名稱
    files_to_backup = ["server_info.txt", "players.txt", "map_pools.txt"]

    # 定義備份資料夾名稱，包含日期和時間
    backup_folder_name = datetime.now().strftime("%Y%m%d%H%M")
    backup_folder_path = os.path.join("DC機器人資料備份", backup_folder_name)

    # 確保備份資料夾存在
    os.makedirs(backup_folder_path, exist_ok=True)

    # 載入要備份的資料
    for filename in files_to_backup:
        # 檔案路徑在與腳本相同的資料夾中
        file_path = os.path.join(os.getcwd(), filename)
        
        if os.path.isfile(file_path):
            shutil.copy(file_path, backup_folder_path)
            print(f"已備份 {filename} 到 {backup_folder_path}")
        else:
            print(f"找不到檔案 {filename}，跳過備份。")
backup_data()
# 讀取地圖池
def load_map_pools():
    if os.path.exists(MAP_POOL_FILE):
        with open(MAP_POOL_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# 寫入地圖池
def save_map_pools():
    with open(MAP_POOL_FILE, 'w', encoding='utf-8') as f:
        json.dump(map_pools, f, ensure_ascii=False, indent=4)

# 使用字典來存儲每個伺服器的地圖池
map_pools = load_map_pools()

# 使用字典來存儲每個伺服器的暫時地圖池
temp_map_pools = {}

# 管理多場比賽的字典
games = {}

# 檢查並讀取現有的角色購買記錄
if os.path.exists('roles.json'):
    with open('roles.json', 'r') as f:
        role_data = json.load(f)
else:
    role_data = {}
        
def load_players():
    if os.path.exists(PLAYERS_FILE):
        with open(PLAYERS_FILE, 'r') as file:
            players = json.load(file)
    else:
        return []
    return players

# 寫入玩家數據
def save_players():
    try:
        with open(PLAYERS_FILE, 'w') as file:
            json.dump(players, file, indent=2)
        print("玩家数据已保存。")  # 添加调试信息
    except Exception as e:
        print(f"保存玩家数据时发生错误: {e}")
		

# 註冊玩家
def register_player(user_id, score, stability, userName):
    players.append({
        'id': user_id,
        'userName': userName,
        'score': score,
        'stability': stability,
        'total_games': 0,
        'wins': 0,
        'losses': 0,
        'team_stats': {},
        'coins': 0,
        'last_check_in': 0,
        'ratings': {},
        'roles': {},  # 新增字段，用于存储购买的角色及其到期时间
        'items': {}  # 新增字段，用于存储道具及其数量
    })
    save_players()
players = load_players()

def calculate_composite_score(player):
    ratings = player.get('ratings', {})
    num_ratings = len(ratings)

    if num_ratings > 0:
        total_rating = sum(ratings.values())
        average_rating = total_rating / num_ratings
        # 使用對數縮放
        scaled_rating = average_rating * math.log(num_ratings + 1)
    else:
        scaled_rating = 0

    composite_score = player['score'] + scaled_rating * 8
    return float(f"{composite_score:.2f}")
    
def balance_teams(participants):
    # 定義特定玩家ID
    special_players = {}
    same_team_probability = 0

    # 尋找特定玩家
    special_participants = [p for p in participants if p['id'] in special_players]

    # 檢查是否需要將特定玩家分到同一隊
    if len(special_participants) == 2 and random.random() < same_team_probability:
        print(f"觸發自動同隊機制")
        if random.choice([True, False]):
            team1 = special_participants
            team2 = []
        else:
            team1 = []
            team2 = special_participants

        # 移除已分配的特定玩家
        remaining_participants = [p for p in participants if p not in special_participants]
    else:
        team1 = []
        team2 = []
        remaining_participants = participants

    # 按照綜合評分排序剩餘的參與者
    remaining_participants.sort(key=calculate_composite_score, reverse=True)

    score1 = sum(calculate_composite_score(p) for p in team1)
    score2 = sum(calculate_composite_score(p) for p in team2)

    # 分配剩餘的參與者
    for player in remaining_participants:
        if score1 <= score2:
            team1.append(player)
            score1 += (calculate_composite_score(player))
        else:
            team2.append(player)
            score2 += (calculate_composite_score(player))

    # 迭代優化
    for _ in range(20):  # 增加迭代次數
        if abs(score1 - score2) > 1:
            # 嘗試交換兩隊中分數最接近的玩家
            for p1 in team1:
                for p2 in team2:
                    new_score1 = score1 - calculate_composite_score(p1) + calculate_composite_score(p2)
                    new_score2 = score2 - calculate_composite_score(p2) + calculate_composite_score(p1)
                    if abs(new_score1 - new_score2) < abs(score1 - score2):
                        team1.remove(p1)
                        team2.remove(p2)
                        team1.append(p2)
                        team2.append(p1)
                        score1 = new_score1
                        score2 = new_score2
                        break

    return team1, team2


def reset_users(new_stability=None):
    # 使用字典來去除重複用戶
    unique_players = {}
    for player in players:
        unique_players[player['id']] = player

    # 將字典轉回列表
    players[:] = unique_players.values()

    # 如果提供了新的穩定度，則更新所有用戶的穩定度
    if new_stability is not None:
        for player in players:
            player['stability'] = new_stability
    # 保存更新後的玩家數據
    save_players()
    print("用戶數據已重整。")


@tasks.loop(minutes=180)  
async def check_roles_expiry_task():
    current_time = datetime.now()

    for player in players:
        if 'roles' not in player:
            continue

        guild = discord.utils.get(bot.guilds, id=959587766017097760)  # 替換為你的伺服器ID
        member = guild.get_member(player['id'])

        if not member:
            continue

        for role_id, expiry_time in list(player['roles'].items()):
            expiry_time = datetime.fromisoformat(expiry_time)

            if current_time >= expiry_time:
                role = guild.get_role(int(role_id))
                if role:
                    try:
                        await member.remove_roles(role)
                        await member.send(f'你的 {role.name} 身分組已到期並被移除。')
                    except discord.HTTPException as e:
                        print(f"移除角色時發生錯誤: {e}")

                del player['roles'][role_id]

    save_players()
    
@tasks.loop(minutes=180)  # 每小時檢查一次
async def check_channels_expiry_task():
    current_time = datetime.now()

    for player in players:
        if 'channels' not in player:
            continue

        guild = discord.utils.get(bot.guilds, id=959587766017097760)  # 替換為你的伺服器ID

        for channel_id, expiry_time in list(player['channels'].items()):
            expiry_time = datetime.fromisoformat(expiry_time)

            if current_time >= expiry_time:
                channel = guild.get_channel(int(channel_id))
                if channel:
                    try:
                        await channel.delete(reason="限時頻道到期自動刪除")
                        await interaction.user.send(f'你的頻道 {channel.name} 已到期並被刪除。')
                    except discord.HTTPException as e:
                        print(f"刪除頻道時發生錯誤: {e}")

                del player['channels'][channel_id]
    save_players()
    update_weather_if_needed()

async def check_channel_expiry():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.now()
        for player in players:
            if 'channels' in player:
                for channel_id, expiry in player['channels'].items():
                    expiry_time = datetime.fromisoformat(expiry)
                    time_remaining = expiry_time - now
                    if 0 < time_remaining.days <= 3:
                        channel = bot.get_channel(int(channel_id))
                        if channel:
                            text_channel = discord.utils.get(channel.guild.text_channels, name=channel.name)
                            if text_channel:
                                await text_channel.send(f"提醒：此頻道將在 {time_remaining.days} 天 {time_remaining.seconds // 3600} 小時後到期。")
        await asyncio.sleep(10800)  # 每3小時檢查一次

def update_weather_if_needed():
    last_update = datetime.fromisoformat(server_info['last_weather_update'])
    now = datetime.now()
    
    # 如果超過 24 小時，則更新天氣效果
    if now - last_update >= timedelta(hours=24):
        server_info['weather'] = random.choice(list(WEATHER_EFFECTS.keys()))
        server_info['weather_multiplier'] = WEATHER_EFFECTS[server_info['weather']]
        server_info['last_weather_update'] = now.isoformat()
        save_server_info(server_info)
        print(f"天氣已更新：{server_info['weather']}，分數增減幅度：{server_info['weather_multiplier']}x")
        
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"已同步 {len(synced)} 個指令")
    except Exception as e:
        print("An error occurred while syncing: ", e)
    check_roles_expiry_task.start()
    check_channels_expiry_task.start()  # 啟動頻道到期檢查任務
    bot.loop.create_task(check_channel_expiry())
    update_weather_if_needed()  # 檢查並更新天氣效果

# 定義事件來監聽訊息並進行轉換
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # 忽略自己的訊息
    
    if message.content.startswith('aoe2de://0'):
        # 回應轉換後的 URL
        await message.channel.send(f"↑↑上方的連結放至瀏覽器連結處後按Enter可加入房間↑↑")
    
    # 呼叫父類別的 on_message 方法，以確保事件處理順序不被中斷
    await bot.process_commands(message)
    

@bot.tree.command(name="註冊", description="註冊玩家並設置初始分數和穩定度")
@app_commands.describe(user="要註冊的用戶", score="玩家分數", stability="玩家穩定度")
async def register(interaction: discord.Interaction, user: discord.User = None, score: int = 1000, stability: float = 10.0):
    # 如果沒有指定用戶，則默認為註冊自己
    if user is None:
        user = interaction.user
        # 一般用戶自行註冊時，強制使用預設的分數和穩定度
        score = 1000
        stability = 5.0

    # 如果指定了用戶且不是自己，檢查是否有管理員權限
    if user != interaction.user and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("你沒有權限註冊其他用戶。", ephemeral=True)
        return

    # 檢查玩家是否已經註冊
    if any(p['id'] == user.id for p in players):
        await interaction.response.send_message(f"{user.name} 已經註冊。", ephemeral=True)
        return
     # 獲取用戶在伺服器中的暱稱
    guild = interaction.guild
    member = guild.get_member(user.id)
    nickname = member.display_name if member else user.name
    # 註冊玩家
    register_player(user.id, score, stability,nickname)
    await interaction.response.send_message(f'{nickname} 已註冊，分數: {score}, 穩定度: {stability}', ephemeral=True)

# 定義每頁顯示的玩家數量
PLAYERS_PER_PAGE = 10
@bot.tree.command(name="排行榜", description="查看所有玩家的積分或金幣排行榜")
async def leaderboard(interaction: discord.Interaction):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return

    # 排序玩家
    sorted_by_score = sorted(players, key=lambda x: x['score'], reverse=True)
    sorted_by_coins = sorted(players, key=lambda x: x['coins'], reverse=True)
    sorted_by_win_rate = sorted(players, key=lambda x: (x['wins'] / x['total_games']) if x['total_games'] > 0 else 0, reverse=True)
    sorted_by_composite_score = sorted(players, key=calculate_composite_score, reverse=True)

    # 創建嵌入消息
    def create_embed(page: int, leaderboard_type: str):
        start = page * PLAYERS_PER_PAGE
        end = start + PLAYERS_PER_PAGE

        if leaderboard_type == "score":
            leaderboard_info = '\n'.join([
                f"{page*PLAYERS_PER_PAGE+i+1}. {interaction.guild.get_member(p['id']).display_name} - 分數: {p['score']}, 穩定性: {p['stability']}, 勝率: {p['wins'] / (p['total_games'] if p['total_games'] > 0 else 1):.2%}"
                for i, p in enumerate(sorted_by_score[start:end]) if p['total_games'] >= 0
            ])
            title = f"積分排行榜 - 第 {page + 1} 頁"
        elif leaderboard_type == "coins":
            leaderboard_info = '\n'.join([
                f"{page*PLAYERS_PER_PAGE+i+1}. {interaction.guild.get_member(p['id']).display_name} - 金幣: {p['coins']}"
                for i, p in enumerate(sorted_by_coins[start:end])
            ])
            title = f"金幣排行榜 - 第 {page + 1} 頁"
        elif leaderboard_type == "win_rate":
            leaderboard_info = '\n'.join([f"{page*PLAYERS_PER_PAGE+i+1}. {interaction.guild.get_member(p['id']).display_name} - 勝率: {p['wins'] / (p['total_games'] if p['total_games'] > 0 else 1):.2%}\n"for i, p in enumerate(sorted_by_win_rate[start:end])])
            title = f"勝率排行榜 - 第 {page + 1} 頁"
        else:  # 綜合評分排行榜
            leaderboard_info = '\n'.join([
                f"{page*PLAYERS_PER_PAGE+i+1}. {interaction.guild.get_member(p['id']).display_name} - 綜合評分: {calculate_composite_score(p)}"
                for i, p in enumerate(sorted_by_composite_score[start:end])
            ])
        title = f"綜合評分排行榜 - 第 {page + 1} 頁"

        embed = Embed(title=title, description=leaderboard_info, color=0x00ff00)
        return embed

    # 創建按鈕視圖
    class LeaderboardView(View):
        def __init__(self, total_pages: int, leaderboard_type: str):
            super().__init__()
            self.current_page = 0
            self.total_pages = total_pages
            self.leaderboard_type = leaderboard_type

        @button(label="上一頁", style=ButtonStyle.primary, disabled=True)
        async def previous_page(self, interaction: Interaction, button):
            self.current_page -= 1
            if self.current_page == 0:
                button.disabled = True
            self.children[1].disabled = False  # Enable next button
            await interaction.response.edit_message(embed=create_embed(self.current_page, self.leaderboard_type), view=self)

        @button(label="下一頁", style=ButtonStyle.primary)
        async def next_page(self, interaction: Interaction, button):
            self.current_page += 1
            if self.current_page == self.total_pages - 1:
                button.disabled = True
            self.children[0].disabled = False  # Enable previous button
            await interaction.response.edit_message(embed=create_embed(self.current_page, self.leaderboard_type), view=self)

    # 創建選擇器
    class LeaderboardTypeSelect(Select):
        def __init__(self):
            options = [
                discord.SelectOption(label="積分排行榜", value="score"),
                discord.SelectOption(label="金幣排行榜", value="coins"),
                discord.SelectOption(label="勝率排行榜", value="win_rate"),
                discord.SelectOption(label="綜合評分排行榜", value="points")  
            ]
            super().__init__(placeholder="選擇排行榜類型", options=options)

        async def callback(self, interaction: Interaction):
            leaderboard_type = self.values[0]
            if leaderboard_type == "score":
                total_pages = (len(sorted_by_score) - 1) // PLAYERS_PER_PAGE + 1
            elif leaderboard_type == "coins":
                total_pages = (len(sorted_by_coins) - 1) // PLAYERS_PER_PAGE + 1
            elif leaderboard_type == "win_rate":
                total_pages = (len(sorted_by_win_rate) - 1) // PLAYERS_PER_PAGE + 1
            else:  
                total_pages = (len(sorted_by_composite_score) - 1) // PLAYERS_PER_PAGE + 1
            view = LeaderboardView(total_pages, leaderboard_type)
            await interaction.response.edit_message(embed=create_embed(0, leaderboard_type), view=view)

    # 創建初始視圖
    view = View()
    view.add_item(LeaderboardTypeSelect())
    await interaction.response.send_message("請選擇要查看的排行榜類型：", view=view, ephemeral=False)

@bot.tree.command(name="評分", description="給其他玩家評分")
@app_commands.describe(target_user="要評分的玩家", rating="評分值")
async def rate_player(interaction: discord.Interaction, target_user: discord.User, rating: int):
    # 检查评分值是否在合理范围内
    if rating < 1 or rating > 5:
        await interaction.response.send_message("评分值必须在1到5之间。", ephemeral=True)
        return

    # 檢查用戶是否嘗試給自己評分
    if interaction.user.id == target_user.id:
        await interaction.response.send_message("你不能給自己評分。", ephemeral=True)
        return
    # 检查目标玩家是否已注册
    target_player = next((p for p in players if p['id'] == target_user.id), None)
    if not target_player:
        await interaction.response.send_message(f"{target_user.name} ;尚未註冊。", ephemeral=True)
        return
    if 'ratings' not in target_player:
        target_player['ratings'] = {}
    # 检查当前用户是否已经给目标玩家评分
    if interaction.user.id in target_player['ratings']:
        await interaction.response.send_message("你已經給該玩家評分，不能重複評分", ephemeral=True)
        return

    # 给目标玩家评分
    target_player['ratings'][interaction.user.id] = rating
    save_players()
    await interaction.response.send_message(f"你已成功给 {target_user.name} 評分：{rating}。", ephemeral=True)

@bot.tree.command(name="查詢評分", description="查詢玩家目前被評分的狀況")
@app_commands.describe(target_user="要查詢的玩家")
async def query_ratings(interaction: discord.Interaction, target_user: discord.User = None):
    # 如果沒有指定用戶，則默認查詢自己
    if target_user is None:
        target_user = interaction.user

    # 檢查目標玩家是否已註冊
    target_player = next((p for p in players if p['id'] == target_user.id), None)
    if not target_player:
        await interaction.response.send_message(f"{target_user.name} 尚未註冊。", ephemeral=True)
        return

    # 獲取玩家的評分信息
    ratings = target_player.get('ratings', {})
    
    if not ratings:
        await interaction.response.send_message(f"{target_user.name} 尚未收到任何評分。", ephemeral=True)
        return

    # 計算平均評分
    average_rating = sum(ratings.values()) / len(ratings)

    # 構建評分信息字串
    rating_details = "\n".join([f"來自 <@{rater_id}> 的評分: {rating}" for rater_id, rating in ratings.items()])
    response_message = ("\n"f"{target_user.name} 的評分狀況：\n"f"平均評分: {average_rating:.2f}\n"f"詳細評分:\n{rating_details}")

    await interaction.response.send_message(response_message, ephemeral=False)


@bot.tree.command(name="查詢分數", description="查詢玩家的分數和穩定性")
async def query_score(interaction: discord.Interaction, user: discord.User):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return
    player = next((p for p in players if p['id'] == user.id), None)
    
    if player:
        win_rate = player['wins'] / player['total_games'] if player['total_games'] > 0 else 0
        embed = Embed(
            title=f"{user.name} 的資訊",
            description=('\n'f"分數: {player['score']}"'\n'f"穩定性: {player['stability']}"'\n'f"勝/敗/總: {player['wins']}/{player['losses']}/{player['total_games']}"'\n'f"勝率: {win_rate:.2%}"),
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("找不到該用戶，請確認用戶已註冊。")

@bot.tree.command(name="查詢合作勝率", description="查詢玩家與特定隊友的合作勝率")
async def query_team_win_rate(interaction: discord.Interaction, user: discord.User, teammate: discord.User):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return
    player = next((p for p in players if p['id'] == user.id), None)
    if player:
        team_stats = player['team_stats'].get(f"{teammate.id}", {'wins': 0, 'total_games': 0})
        win_rate = team_stats['wins'] / team_stats['total_games'] if team_stats['total_games'] > 0 else 0
        embed = Embed(
            title=f"{user.name} 與 {teammate.name} 的合作勝率",
            description=f"勝/總: {team_stats['wins']}/{team_stats['total_games']}, 勝率: {win_rate:.2%}",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("找不到該用戶，請確認用戶已註冊。")

def distribute_rewards(game_id, winning_team):
    if 'bets' not in games[game_id]:
        return

    total_bets = sum(bet['amount'] for bet in games[game_id]['bets'][winning_team])
    if total_bets == 0:
        return

    total_pool = sum(bet['amount'] for team in games[game_id]['bets'].values() for bet in team)

    for bet in games[game_id]['bets'][winning_team]:
        player = next((p for p in players if p['id'] == bet['id']), None)
        if player:
            reward = (bet['amount'] / total_bets) * total_pool
            player['coins'] += reward

    save_players()

def generate_unique_game_id():
    while True:
        game_id = str(random.randint(1000, 9999))
        if game_id not in games:
            return game_id

@bot.tree.command(name="創建比賽", description="創建一場新的比賽")
async def create_game(interaction: Interaction):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return

    game_id = generate_unique_game_id()
    games[game_id] = {
        'participants': [],
        'started': False,
        'result_decided': False,  # 用於記錄比賽結果是否已經決定
        'used_items' : False
    }
    result_view = View(timeout=3600*3)
    async def update_participant_list():
        participants = games[game_id]['participants']
        participant_list = '\n'.join([f"{interaction.guild.get_member(p['id']).display_name} - 分數: {p['score']} 穩定性: {p['stability']} | 綜合評分: {calculate_composite_score(p)}" for p in participants]) or "目前無人參加"
        embed = Embed(title=f"房間 {game_id} 參加者名單({len(games[game_id]['participants'])})人", description=participant_list, color=0x00ff00)
        await interaction.edit_original_response(embed=embed, view=view)

    async def join_game_callback(interaction: Interaction):
        user_id = interaction.user.id

        if len(games[game_id]['participants']) >= 8:
            await interaction.response.send_message("房間已滿，無法加入。", ephemeral=True)
            return

        if any(p['id'] == user_id for p in games[game_id]['participants']):
            await interaction.response.send_message("你已經加入了這場比賽。", ephemeral=True)
            return

        player_info = next((p for p in players if p['id'] == user_id), None)
        if not player_info:
            await interaction.response.send_message("你的資料不在系統中，請聯繫管理員。", ephemeral=True)
            return

        games[game_id]['participants'].append({
            'id': player_info['id'],
            'userName': player_info['userName'],
            'score': player_info['score'],
            'stability': player_info['stability'],
            'total_games': player_info['total_games'],
            'wins': player_info['wins'],
            'losses': player_info['losses'],
            'team_stats': player_info['team_stats'],
            'coins': player_info['coins'],
            'last_check_in': player_info['last_check_in'],
            'ratings': player_info.get('ratings',{}),
        })
        await update_participant_list()
        await interaction.response.send_message("加入了這場比賽。", ephemeral=True)

    async def cancel_game_callback(interaction: Interaction):
        user_id = interaction.user.id
        games[game_id]['participants'] = [p for p in games[game_id]['participants'] if p['id'] != user_id]
        await update_participant_list()
        await interaction.response.send_message("離開了這場比賽。", ephemeral=True)

    async def start_game_callback(interaction: Interaction):
        try:
            if games[game_id]['started']:
                await interaction.response.send_message("比賽已經開始。", ephemeral=True)
                return

            participants = games[game_id]['participants']
            if len(participants) < 8:
                await interaction.response.send_message("參加人數不足，無法開始比賽。", ephemeral=True)
                return

            games[game_id]['started'] = True
            team1, team2 = balance_teams(participants)

            games[game_id]['team1'] = team1
            games[game_id]['team2'] = team2

            team1_info = '\n'.join([f"{interaction.guild.get_member(p['id']).display_name} - 分數: {p['score']} 穩定性: {p['stability']} | 綜合評分: {calculate_composite_score(p)}"for p in team1])
            team2_info = '\n'.join([f"{interaction.guild.get_member(p['id']).display_name} - 分數: {p['score']} 穩定性: {p['stability']} | 綜合評分: {calculate_composite_score(p)}"for p in team2])
            button1 = Button(label="Team 1 勝利", style=ButtonStyle.green)
            button2 = Button(label="Team 2 勝利", style=ButtonStyle.red)

            button1.callback = button1_callback
            button2.callback = button2_callback

            result_view.clear_items()  # 清除之前的按鈕
            result_view.add_item(button1)
            result_view.add_item(button2)

            embed = Embed(title=f"房間 {game_id} 開始！", description=f"**Team 1:**\n{team1_info}\n\n**Team 2:**\n{team2_info}", color=0x00ff00)
            await interaction.response.send_message(embed=embed, view=result_view)
        except Exception as e:
            await interaction.response.send_message(f"發生錯誤: {str(e)}", ephemeral=True)


    async def button1_callback(interaction: Interaction):
        if games[game_id]['result_decided']:
            await interaction.response.send_message("比賽結果已經決定，無法再次操作。", ephemeral=True)
            return
    
        # 顯示確認視窗
        class ConfirmModal(Modal):
            def __init__(self):
                super().__init__(title="確認 Team 1 勝利")
    
                self.confirm_input = TextInput(label="請輸入 '確認' 以確認 Team 1 勝利", placeholder="確認")
                self.add_item(self.confirm_input)
            async def on_submit(self, interaction: Interaction):
                await interaction.response.defer()  # 延遲回應，避免交互過期
                if self.confirm_input.value.lower() == "確認":
                    try:
                        games[game_id]['result_decided'] = True
                        games[game_id]['started'] = "team1_won"
                        team1 = games[game_id]['team1']
                        team2 = games[game_id]['team2']
    
                        # 記錄按下按鈕的人
                        winner_decider = interaction.user.display_name
                        # 假設 adjust_scores 函數返回分數變動
                        changedValue = adjust_scores(team1, team2,game_id)
    
                        # 更新後的分數和變動顯示
                        team1_info = '\n'.join(
                            [f"{interaction.guild.get_member(p['id']).display_name} - 分數: {p['score']} ({changedValue[0][p['id']]}), 穩定度: {p['stability']}({changedValue[1][p['id']]})" for p in team1]
                        )
                        team2_info = '\n'.join(
                            [f"{interaction.guild.get_member(p['id']).display_name} - 分數: {p['score']} ({changedValue[0][p['id']]}), 穩定度: {p['stability']}({changedValue[1][p['id']]})" for p in team2]
                        )
    
                        # 顯示道具使用者
                        used_item_by = games[game_id].get('used_item_by', None)
                        used_item_effect = games[game_id].get('used_item_effect', None)
                        item_info = f"\n\n**道具使用者:** {used_item_by}\n**道具效果:** {used_item_effect}" if used_item_by else ""
                        embed = Embed(
                            title=f"Team 1 勝利！ - 房間 {game_id} 結束！",
                            description=f"**Team 1 成員:**\n{team1_info}\n\n**Team 2 成員:**\n{team2_info}**\n\n按下勝利按鈕的人:** {winner_decider}{item_info}",color=0x00ff00
                        )
                        distribute_rewards(game_id, 'team1')
                        await interaction.edit_original_response(embed=embed, view=result_view)
                        del games[game_id]
                    except discord.errors.NotFound:
                        print("交互已过期，无法响应。")
                    except Exception as e:
                        print(f"发生错误: {str(e)}")
                else:
                    await interaction.response.send_message("確認失敗，請輸入正確的確認文字。", ephemeral=True)
    
        await interaction.response.send_modal(ConfirmModal())
    
    async def button2_callback(interaction: Interaction):
        if games[game_id]['result_decided']:
            await interaction.response.send_message("比賽結果已經決定，無法再次操作。", ephemeral=True)
            return
    
        # 顯示確認視窗
        class ConfirmModal(Modal):
            def __init__(self):
                super().__init__(title="確認 Team 2 勝利")
                self.confirm_input = TextInput(label="請輸入 '確認' 以確認 Team 2 勝利", placeholder="確認")
                self.add_item(self.confirm_input)
    
            async def on_submit(self, interaction: Interaction):
                await interaction.response.defer()  # 延遲回應，避免交互過期
                if self.confirm_input.value.lower() == "確認":
                    try:
                        games[game_id]['result_decided'] = True
                        games[game_id]['started'] = "team2_won"
                        team1 = games[game_id]['team1']
                        team2 = games[game_id]['team2']
    
                        # 記錄按下按鈕的人
                        winner_decider = interaction.user.display_name
                        # 假設 adjust_scores 函數返回分數變動
                        changedValue = adjust_scores(team2, team1,game_id)
    
                        # 更新後的分數和變動顯示
                        team1_info = '\n'.join(
                            [f"{interaction.guild.get_member(p['id']).display_name} 分數: {p['score']} ({changedValue[0][p['id']]}), 穩定度: {p['stability']}({changedValue[1][p['id']]})" for p in team1]
                        )
                        team2_info = '\n'.join(
                            [f"{interaction.guild.get_member(p['id']).display_name} 分數: {p['score']} ({changedValue[0][p['id']]}), 穩定度: {p['stability']}({changedValue[1][p['id']]})" for p in team2]
                        )
                        # 顯示道具使用者
                        used_item_by = games[game_id].get('used_item_by', None)
                        used_item_effect = games[game_id].get('used_item_effect', None)
                        item_info = f"\n\n**道具使用者:** {used_item_by}\n**道具效果:** {used_item_effect}" if used_item_by else ""
                        embed = Embed(
                            title=f"Team 2 勝利！ - 房間 {game_id} 結束！",
                            description=f"**Team 1 成員:**\n{team1_info}\n\n**Team 2 成員:**\n{team2_info}**\n\n按下勝利按鈕的人:** {winner_decider}{item_info}",color=0x00ff00
                        )
                        distribute_rewards(game_id, 'team2')
                        await interaction.edit_original_response(embed=embed, view=result_view)
                        del games[game_id]
                    except discord.errors.NotFound:
                        print("交互已过期，无法响应。")
                    except Exception as e:
                        print(f"发生错误: {str(e)}")
                else:
                    await interaction.response.send_message("確認失敗，請輸入正確的確認文字。", ephemeral=True)
    
        await interaction.response.send_modal(ConfirmModal())


    async def update_interface_callback(interaction: Interaction):
        await update_participant_list()
        await interaction.response.send_message("介面已更新。", ephemeral=True)

    join_button = Button(label="加入比賽", style=ButtonStyle.primary)
    cancel_button = Button(label="取消參加", style=ButtonStyle.danger)
    start_button = Button(label="開始比賽", style=ButtonStyle.green)
    update_button = Button(label="更新介面", style=ButtonStyle.secondary)

    join_button.callback = join_game_callback
    cancel_button.callback = cancel_game_callback
    start_button.callback = start_game_callback
    update_button.callback = update_interface_callback

    view = View()
    view.add_item(join_button)
    view.add_item(cancel_button)
    view.add_item(start_button)
    view.add_item(update_button)

    await interaction.response.send_message(f'房間已創建，ID: {game_id}。點擊按鈕加入或取消參加比賽。', view=view)
    await update_participant_list()

    async def update_result_view_periodically(interaction, result_view, game_id):
        while not games[game_id]['result_decided']:
            await asyncio.sleep(600)  # 每10分鐘更新一次
            try:
                # 檢查消息是否存在
                message = await interaction.original_response()
                if message:
                    await interaction.edit_original_response(view=result_view)
                else:
                    print("原始消息已不存在。")
                    break
    
            except discord.errors.NotFound:
                print("原始消息已不存在。")
                break
            except discord.errors.HTTPException as e:
                print(f"HTTP 錯誤: {e}")
                # 可以選擇在這裡重試或記錄錯誤
    
    # 在創建比賽時啟動定期更新任務
    asyncio.create_task(update_result_view_periodically(interaction, result_view, game_id))

def find_active_game_for_user(user_id):
    for game_id, game in games.items():
        if not game['started'] and any(p['id'] == user_id for p in game['participants']):
            return game_id

@bot.tree.command(name="投注", description="投注金幣在某個隊伍的勝利")
async def place_bet(interaction: Interaction,game_id: int ,team: str, amount: int):
    user_id = interaction.user.id

    player = next((p for p in players if p['id'] == user_id), None)
    if not player:
        await interaction.response.send_message("你尚未註冊，請先註冊後再投注。", ephemeral=True)
        return

    if player['coins'] < amount:
        await interaction.response.send_message("你的金幣不足，無法投注這麼多金幣。", ephemeral=True)
        return

    if game_id not in games or games[game_id]['started']:
        await interaction.response.send_message("目前沒有可投注的比賽或比賽已經開始。", ephemeral=True)
        return

    if team not in ['team1', 'team2']:
        await interaction.response.send_message("請選擇正確的隊伍（team1 或 team2）。", ephemeral=True)
        return

    player['coins'] -= amount
    games[game_id]['bets'][team].append({'id': user_id, 'amount': amount})

    save_players()

    await interaction.response.send_message(f"你已成功投注 {amount} 金幣在 {team} 勝利。", ephemeral=True)

    return None
def record_team_match(player_id, teammate_id, result):
    player = next((p for p in players if p['id'] == player_id), None)
    if player:
        if teammate_id not in player['team_stats']:
            player['team_stats'][teammate_id] = {'wins': 0, 'total_games': 0}
        
        player['team_stats'][teammate_id]['total_games'] += 1
        if result == 'win':
            player['team_stats'][teammate_id]['wins'] += 1
        

def update_player_data(player):
    for p in players:
        if p['id'] == player['id']:
            p['score'] = player['score']
            p['stability'] = player['stability']
            p['total_games'] = player['total_games']
            p['wins'] = player['wins']
            p['losses'] = player['losses']
            p['coins'] = player.get('coins',0) or 0
            p['last_check_in'] = player.get('last_check_in') or "2025-01-01"
            break
# 定义文件路径
SERVER_INFO_FILE = 'server_info.txt'

def initialize_server_info():
    server_info = {
        'total_matches_played': 0,
        'dragon_gate_coins': 0,
        'weather': "晴天",
        'weather_multiplier': 1.0,
        'last_weather_update': datetime.now().isoformat()  # 上次更新時間
    }
    
    if os.path.exists(SERVER_INFO_FILE):
        with open(SERVER_INFO_FILE, 'r') as file:
            for line in file:
                if line.startswith("Total Matches Played:"):
                    server_info['total_matches_played'] = int(line.split(":")[1].strip())
                elif line.startswith("Dragon Gate Coins:"):
                    server_info['dragon_gate_coins'] = int(line.split(":")[1].strip())
                elif line.startswith("Weather:"):
                    server_info['weather'] = line.split(":")[1].strip()
                elif line.startswith("Weather Multiplier:"):
                    server_info['weather_multiplier'] = float(line.split(":")[1].strip())
                elif line.startswith("Last Weather Update:"):
                    server_info['last_weather_update'] = line.split(":")[1].strip()
    return server_info

# 初始化伺服器信息
server_info = initialize_server_info()
total_matches_played =server_info['total_matches_played']
def save_server_info(server_info):
    with open(SERVER_INFO_FILE, 'w') as file:
        file.write(f"Total Matches Played: {server_info['total_matches_played']}\n")
        file.write(f"Dragon Gate Coins: {server_info['dragon_gate_coins']}\n")
        file.write(f"Weather: {server_info['weather']}\n")
        file.write(f"Weather Multiplier: {server_info['weather_multiplier']}\n")
        file.write(f"Last Weather Update: {server_info['last_weather_update']}\n")
        

save_server_info(server_info)
def calculate_stability_change(opponent_win_rate, player_total_games, total_matches_played, total_players, current_stability):
    # 调整基础稳定度变化范围
    base_stability_change = 1.5 if opponent_win_rate >= 0.8 else -3

    # 根据总场数、玩家总场数和玩家总数缩放变化量
    player_influence = player_total_games / max(1, total_matches_played)
    scaling_factor = 1 / (1 + player_influence * 3 + (total_players / 200))

    # 确保缩放因子在合理范围内
    scaling_factor = max(0.1, min(1, scaling_factor))

    # 根据当前稳定度调整稳定度变化
    # 稳定度越低，变化越小
    if current_stability >= 5:
        stability_change = base_stability_change * scaling_factor * (0.3 + (current_stability / 10))
    else:
        stability_change = base_stability_change * scaling_factor * (0.05 + (current_stability / 10))

    return stability_change


def adjust_scores(winning_team, losing_team,game_id):
    global total_matches_played
    total_matches_played += 1  # 每次调用此函数时，增加总进行场数

    all_players = winning_team + losing_team
    average_score = sum(player['score'] for player in all_players) / len(all_players)

    base_score_increase = 20
    base_score_decrease = 20
    
    # 應用天氣效果
    weather = server_info.get('weather', "晴天")  # 默認為晴天
    weather_multiplier = server_info.get('weather_multiplier', 1.0)
    if game_id in games and 'used_item_effect' in games[game_id] and games[game_id]['used_item_effect'] != 'ignore_weather':
        base_score_increase *= weather_multiplier
        base_score_decrease *= weather_multiplier
        
    # 應用道具效果
    if game_id in games and 'used_item_effect' in games[game_id]:
        effect = games[game_id]['used_item_effect']
        if effect == "increase_score_multiplier":
            base_score_increase *= 1.2
            base_score_decrease *= 1.2
        elif effect == "decrease_score_multiplier":
            base_score_increase *= 0.8
            base_score_decrease *= 0.8
        elif effect == "reverse_score":
            if random.random() < 0.5:
                base_score_increase *= -1
                base_score_decrease *= -1
        elif effect == "double_score":
            base_score_increase *= 2
            base_score_decrease *= 2
        # 其他道具效果（如增加穩定性）可以在這裡處理
    
    score_changes = {}
    stability_changes = {}
    for player in winning_team:
        score_difference = player['score'] - average_score
        score_increase = base_score_increase * ((1 - score_difference / average_score) **2 )
        score_increase *= (1 + (player['stability']) / 10)

        score_change = max(1, min(40, score_increase))
        player['score'] += score_change
        player['score'] = round(player['score'], 2)

        if len(losing_team) > 0:
            opponent_win_rate = sum(
                p.get('wins', 0) / max(1, p.get('total_games', 1)) for p in losing_team if p.get('total_games', 0) > 0
            ) / len(losing_team)
        else:
            opponent_win_rate = 0  # 或者其他適當的預設值
        
        # 根据对手的胜率和总场数调整稳定度
        stability_change = calculate_stability_change(opponent_win_rate,sum(max(1, p.get('total_games', 1)) for p in winning_team if p.get('total_games', 0) > 0),total_matches_played,len(all_players),player['stability'])
        player['stability'] = max(0, min(5, player['stability'] + stability_change))
        player['stability'] = round(player['stability'], 2)  # 保留小數點兩位
        player['total_games'] += 1
        player['wins'] += 1

        for teammate in winning_team:
            if teammate['id'] != player['id']:
                record_team_match(player['id'], teammate['id'], 'win')

        update_player_data(player)

        score_changes[player['id']] = f"+{score_change:.2f}"
        stability_changes[player['id']] = f"{stability_change:.2f}"

    for player in losing_team:
        score_difference = player['score'] - average_score
        score_decrease = base_score_decrease * ((1 + score_difference / average_score)**2)
        score_decrease *= (1 + (player['stability']) / 10)

        score_change = max(1, min(40, score_decrease))
        player['score'] -= score_change
        player['score'] = round(player['score'], 2)

        if len(winning_team) > 0:
            opponent_win_rate = sum(
                p.get('wins', 0) / max(1, p.get('total_games', 1)) for p in winning_team if p.get('total_games', 0) > 0
            ) / len(winning_team)
        else:
            opponent_win_rate = 0  # 或者其他適當的預設值
        # 根据对手的胜率和总场数调整稳定度
        stability_change = calculate_stability_change(opponent_win_rate,sum(max(1, p.get('total_games', 1)) for p in losing_team if p.get('total_games', 0) > 0),total_matches_played,len(all_players),player['stability'])
        player['stability'] = max(0, min(5, player['stability'] + stability_change))
        player['stability'] = round(player['stability'], 2)  # 保留小數點兩位
        player['total_games'] += 1
        player['losses'] += 1

        for teammate in losing_team:
            if teammate['id'] != player['id']:
                record_team_match(player['id'], teammate['id'], 'loss')

        update_player_data(player)

        score_changes[player['id']] = f"-{score_change:.2f}"
        stability_changes[player['id']] = f"{stability_change:.2f}"

    save_players()
    save_server_info(server_info)  # 保存总进行场数

    return [score_changes,stability_changes]
	
@bot.tree.command(name="總地圖-新增", description="添加地圖到總地圖池")
@app_commands.describe(map_name="地圖名稱")
async def add_map(interaction: discord.Interaction, map_name: str):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return

    guild_id = str(interaction.guild_id)
    if guild_id not in map_pools:
        map_pools[guild_id] = []

    # 檢查地圖是否已存在
    if map_name in map_pools[guild_id]:
        await interaction.response.send_message(f"地圖 '{map_name}' 已經存在於總地圖池中！")
    else:
        map_pools[guild_id].append(map_name)
        save_map_pools()
        await interaction.response.send_message(f"地圖 '{map_name}' 已添加到總地圖池！")


# 從總地圖池移除地圖
@bot.tree.command(name="總地圖-移除", description="從總地圖池移除地圖")
async def remove_map(interaction: discord.Interaction):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return

    guild_id = str(interaction.guild_id)
    if guild_id not in map_pools or not map_pools[guild_id]:
        await interaction.response.send_message("總地圖池中沒有可用的地圖。", ephemeral=True)
        return

    # 获取总地图池中的地图
    available_maps = map_pools[guild_id]

    # 创建选择菜单选项
    options = [SelectOption(label=map_name, value=map_name) for map_name in available_maps]

    # 定义选择菜单
    select = Select(
        placeholder="選擇要移除的地圖",
        options=options,
        min_values=1,
        max_values=len(options)  # 允许选择多个地图
    )

    # 定义选择菜单的回调函数
    async def select_callback(interaction: Interaction):
        selected_maps = select.values
        removed_maps = []

        for map_name in selected_maps:
            if map_name in map_pools[guild_id]:
                map_pools[guild_id].remove(map_name)
                removed_maps.append(map_name)

        save_map_pools()

        if removed_maps:
            await interaction.response.send_message(f"地圖 {', '.join(removed_maps)} 已從總地圖池移除！")
        else:
            await interaction.response.send_message("沒有地圖被移除，請確認地圖名稱是否正確！")

    # 将回调函数绑定到选择菜单
    select.callback = select_callback

    # 创建一个视图并将选择菜单添加到视图中
    view = View()
    view.add_item(select)

    # 发送消息并附加视图
    await interaction.response.send_message("請選擇要移除的地圖：", view=view)
    
# 查看當前總地圖池
@bot.tree.command(name="總地圖池-查看", description="查看當前總地圖池")
async def view_maps(interaction: discord.Interaction):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return
    guild_id = str(interaction.guild_id)
    if guild_id in map_pools and map_pools[guild_id]:
        maps_list = ', '.join(map_pools[guild_id])
        await interaction.response.send_message(f"當前總地圖池：{maps_list}")
    else:
        await interaction.response.send_message("總地圖池目前是空的！")

# 隨機選擇地圖從暫時地圖池
@bot.tree.command(name="抽圖", description="隨機選擇一個地圖從暫時地圖池")
async def roll_map(interaction: discord.Interaction):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return
    guild_id = str(interaction.guild_id)
    if guild_id in temp_map_pools and temp_map_pools[guild_id]:
        selected_map = random.choice(temp_map_pools[guild_id])
        maps_list = ', '.join(temp_map_pools[guild_id])
        await interaction.response.send_message(f"隨機選擇的地圖是：{selected_map}\n暫時地圖池：{maps_list}")
    else:
        await interaction.response.send_message("暫時地圖池目前是空的，請先添加地圖！")

# 添加地圖到暫時地圖池
@bot.tree.command(name="暫時地圖-新增", description="添加地圖到暫時地圖池")
@app_commands.describe(map_name="地圖名稱")
async def add_temp_map(interaction: discord.Interaction, map_name: str):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return
    guild_id = str(interaction.guild_id)
    if guild_id not in temp_map_pools:
        temp_map_pools[guild_id] = []
    temp_map_pools[guild_id].append(map_name)
    await interaction.response.send_message(f"地圖 '{map_name}' 已添加到暫時地圖池！")

# 從暫時地圖池移除地圖
@bot.tree.command(name="暫時地圖-移除", description="從暫時地圖池移除地圖")
@app_commands.describe(map_name="地圖名稱")
async def remove_temp_map(interaction: discord.Interaction, map_name: str):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return
    guild_id = str(interaction.guild_id)
    if guild_id in temp_map_pools and map_name in temp_map_pools[guild_id]:
        temp_map_pools[guild_id].remove(map_name)
        await interaction.response.send_message(f"地圖 '{map_name}' 已從暫時地圖池移除！")
    else:
        await interaction.response.send_message(f"地圖 '{map_name}' 不在暫時地圖池中！")

# 查看暫時地圖池
@bot.tree.command(name="暫時地圖-查看", description="查看暫時地圖池")
async def view_temp_maps(interaction: discord.Interaction):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return
    guild_id = str(interaction.guild_id)
    if guild_id in temp_map_pools and temp_map_pools[guild_id]:
        maps_list = ', '.join(temp_map_pools[guild_id])
        await interaction.response.send_message(f"暫時地圖池：{maps_list}")
    else:
        await interaction.response.send_message("暫時地圖池目前是空的！")

# 清空暫時地圖池
@bot.tree.command(name="暫時地圖-清空", description="清空暫時地圖池")
async def clear_temp_map(interaction: discord.Interaction):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return
    guild_id = str(interaction.guild_id)
    temp_map_pools[guild_id] = []
    await interaction.response.send_message("暫時地圖池已清空！")

from discord import SelectOption, Interaction
from discord.ui import Select, View

@bot.tree.command(name="從總地圖快速新增暫時地圖池", description="從總地圖池快速添加地圖到暫時地圖池")
async def quick_add_temp_map(interaction: discord.Interaction):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return

    guild_id = str(interaction.guild_id)
    if guild_id not in map_pools:
        await interaction.response.send_message("總地圖池中沒有可用的地圖。", ephemeral=True)
        return

    # 获取总地图池中的地图
    available_maps = map_pools.get(guild_id, [])

    # 创建选择菜单选项
    options = [SelectOption(label=map_name, value=map_name) for map_name in available_maps]

    # 定义选择菜单
    select = Select(
        placeholder="選擇要添加的地圖",
        options=options,
        min_values=1,
        max_values=len(options)  # 允许选择多个地图
    )

    # 定义选择菜单的回调函数
    async def select_callback(interaction: Interaction):
        selected_maps = select.values
        if guild_id not in temp_map_pools:
            temp_map_pools[guild_id] = []

        added_maps = []
        for map_name in selected_maps:
            if map_name not in temp_map_pools[guild_id]:
                temp_map_pools[guild_id].append(map_name)
                added_maps.append(map_name)

        if added_maps:
            await interaction.response.send_message(f"地圖 {', '.join(added_maps)} 已從總地圖池快速添加到暫時地圖池！")
        else:
            await interaction.response.send_message("沒有地圖被添加，請確認地圖名稱是否正確！")

    # 将回调函数绑定到选择菜单
    select.callback = select_callback

    # 创建一个视图并将选择菜单添加到视图中
    view = View()
    view.add_item(select)

    # 发送消息并附加视图
    await interaction.response.send_message("請選擇要添加的地圖：", view=view)


@bot.tree.command(name="快速新增暫時地圖池", description="快速新增暫時地圖池")
@app_commands.describe(map_names="地圖名稱（用逗號分隔）")
async def quick_add_temp_map(interaction: discord.Interaction, map_names: str):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return
    guild_id = str(interaction.guild_id)

    # 如果暫時地圖池不存在，則初始化
    if guild_id not in temp_map_pools:
        temp_map_pools[guild_id] = []

    # 將用戶輸入的地圖名稱轉換為列表
    map_list = [map_name.strip() for map_name in map_names.split(',') if map_name.strip()]

    # 直接添加地圖到暫時地圖池
    temp_map_pools[guild_id].extend(map_list)

    # 回覆用戶，告知添加的地圖
    if map_list:
        await interaction.response.send_message(f"地圖 {', '.join(map_list)} 已添加到暫時地圖池！")
    else:
        await interaction.response.send_message("沒有地圖被添加，請提供有效的地圖名稱！")
@bot.tree.command(name="抽", description="從提供的列表中隨機抽取一個項目")
@app_commands.describe(items="以逗號分隔的項目列表", purpose="抽的目的（可選）")
async def draw_item(interaction: discord.Interaction, items: str, purpose: str = None):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return
    # 將用戶輸入的項目列表轉換為字串列表
    item_list = [item.strip() for item in items.split(',') if item.strip()]

    # 檢查列表是否為空
    if not item_list:
        await interaction.response.send_message("請提供至少一個有效的項目。")
        return

    # 隨機選擇一個項目
    selected_item = random.choice(item_list)

    # 格式化原始列表
    original_list = ', '.join(item_list)

    # 如果提供了抽的目的，則添加到回覆訊息中
    if purpose:
        response_message += f"\n抽取目的：{purpose}"
		
    # 構建回覆訊息
    response_message = f"原始列表：{original_list}\n隨機抽取的項目是：『{selected_item}』"


    # 回覆用戶
    await interaction.response.send_message(response_message)

@bot.tree.command(name="計算機", description="計算四則運算表達式 例如：/計算機 3 + 5 * 2")
@app_commands.describe(expression="輸入要計算的表達式")
async def calculate(interaction: discord.Interaction, expression: str):
    try:
        # 使用 eval() 計算表達式
        result = eval(expression)
        await interaction.response.send_message(f"結果：{result}")
    except Exception as e:
        await interaction.response.send_message(f"錯誤：{e}，請輸入有效的運算表達式。")

@bot.tree.command(name="批量註冊", description="註冊伺服器中所有具有特定身分組的用戶")
@app_commands.describe(score="玩家分數", stability="玩家穩定度")
async def bulk_register(interaction: discord.Interaction, score: int, stability: float):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("只有管理員可以使用此指令。", ephemeral=True)
        return
    # 定義需要的身分組名稱
    required_role_name = "世紀帝國玩家"
    registered_users = []

    # 遍歷伺服器中的所有成員
    for member in interaction.guild.members:
        # 檢查成員是否擁有特定身分組
        if any(role.name == required_role_name for role in member.roles):
            # 檢查玩家是否已經註冊
            if not any(p['id'] == member.id for p in players):
                # 註冊玩家
                register_player(member.id, score, stability,member.display_name)
                # 使用暱稱或用戶名
                registered_users.append(member.display_name)

    # 回應註冊結果
    if registered_users:
        await interaction.response.send_message(f"以下用戶已註冊：{', '.join(registered_users)}，分數: {score}, 穩定度: {stability}", ephemeral=True)
    else:
        await interaction.response.send_message("沒有新的用戶被註冊，可能所有符合條件的用戶已經註冊過。", ephemeral=True)

@bot.tree.command(name="重整用戶", description="刪除重複用戶並重新設定所有人的穩定度")
@app_commands.describe(stability="新的穩定度（可選）")
async def reset(interaction: discord.Interaction, stability: float = None):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("只有管理員可以使用此指令。", ephemeral=True)
        return
    reset_users(new_stability=stability)
    await interaction.response.send_message(f"用戶數據已重整。所有用戶的穩定度設置為: {stability if stability is not None else '未更改'}")
	
@bot.tree.command(name="指定加入比賽", description="指定加入比賽")
@app_commands.describe(room_id="比賽房間號", user_mentions="要加入比賽的用戶，使用@標記並用逗號分隔")
async def assign_to_game(interaction: discord.Interaction, room_id: int, user_mentions: str):
    # 檢查是否為管理員
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("只有管理員可以使用此指令。", ephemeral=True)
        return

    # 檢查房間是否存在
    if str(room_id) not in games:
        await interaction.response.send_message(f"房間號 {room_id} 不存在。", ephemeral=True)
        return

    # 準備回應訊息
    response_messages = []

    # 解析用戶標籤
    user_mentions_list = user_mentions.split(',')
    for mention in user_mentions_list:
        mention = mention.strip()
        if mention.startswith('<@') and mention.endswith('>'):
            user_id = int(mention[2:-1].replace('!', ''))
            user = interaction.guild.get_member(user_id)
        else:
            response_messages.append(f"無效的用戶標籤: {mention}")
            continue

        if user is None:
            response_messages.append(f"找不到用戶: {mention}")
            continue

        # 檢查房間是否已滿
        if len(games[str(room_id)]['participants']) >= 8:
            response_messages.append(f"房間 {room_id} 已滿，無法加入更多參加者。")
            break

        # 檢查使用者是否已經在房間中
        if any(p['id'] == user.id for p in games[str(room_id)]['participants']):
            response_messages.append(f"<@{user.id}> 已經在房間 {room_id} 中。")
            continue

        # 檢查使用者是否已註冊
        player_info = next((p for p in players if p['id'] == user.id), None)
        if not player_info:
            response_messages.append(f"<@{user.id}> 的資料不在系統中，請聯繫管理員。")
            continue

        # 將使用者加入房間
        games[str(room_id)]['participants'].append({
            'id': player_info['id'],
            'userName': player_info['userName'],
            'score': player_info['score'],
            'stability': player_info['stability'],
            'total_games': player_info['total_games'],
            'wins': player_info['wins'],
            'losses': player_info['losses'],
            'team_stats': player_info['team_stats']
        })
        response_messages.append(f"<@{user.id}> 已被指定加入房間 {room_id}。")

    # 發送回應訊息
    await interaction.response.send_message("\n".join(response_messages), ephemeral=True)

@bot.tree.command(name="隨機加入", description="隨機加入8位玩家到指定的比賽")
@app_commands.describe(game_id="要加入的比賽ID")
async def random_join(interaction: discord.Interaction, game_id: str):
    # 檢查是否是特定用戶進行的操作
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("你沒有權限使用這個指令。", ephemeral=True)
        return

    # 檢查比賽是否存在
    if game_id not in games:
        await interaction.response.send_message("找不到指定的比賽。", ephemeral=True)
        return

    # 隨機選擇8位玩家加入比賽
    available_players = [p for p in players if p['id'] not in [participant['id'] for participant in games[game_id]['participants']]]
    random.shuffle(available_players)
    for player in available_players[:8]:
        if len(games[game_id]['participants']) < 8:
            games[game_id]['participants'].append({
                'id': player['id'],
                'userName': player['userName'],
                'score': player['score'],
                'stability': player['stability'],
                'total_games': player['total_games'],
                'wins': player['wins'],
                'losses': player['losses'],
                'team_stats': player['team_stats']
            })

    # 更新參加者列表
    participants = games[game_id]['participants']
    participant_list = '\n'.join([f"{interaction.guild.get_member(p['id']).display_name} 分數: {p['score']} 穩定性: {p['stability']}" for p in participants]) or "目前無人參加"
    embed = Embed(title=f"房間 {game_id} 參加者名單", description=participant_list, color=0x00ff00)
    await interaction.response.send_message(embed=embed)
@bot.tree.command(name="修改所有分數", description="管理者快速修改所有玩家的分数")
@app_commands.describe(score_change="分数变化（可以是正数或负数）")
async def adjust_all_scores(interaction: discord.Interaction, score_change: int):
    # 检查是否是特定用户进行的操作
    if interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("你没有权限使用这个指令。", ephemeral=True)
        return
    # 修改所有玩家的分数
    for player in players:
        player['score'] += score_change

    # 保存更新后的玩家数据
    save_players()

    await interaction.response.send_message(f"所有玩家的分数已调整，变动: {score_change}")
	
@bot.tree.command(name="調整分數", description="調整指定玩家的分數")
@app_commands.describe(user="要調整分數的用戶", score_change="分數變化（可以是正數或負數）")
async def adjust_score(interaction: discord.Interaction, user: discord.User, score_change: int):
    # 檢查是否是特定用戶進行的調整
    if interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("你沒有權限調整其他用戶的分數。", ephemeral=True)
        return

    # 查找指定用戶
    player = next((p for p in players if p['id'] == user.id), None)
    if player:
        # 獲取用戶在伺服器中的暱稱
        guild = interaction.guild
        member = guild.get_member(user.id)
        nickname = member.display_name if member else user.name

        # 調整分數
        player['score'] += score_change
        save_players()
        await interaction.response.send_message(f"{nickname} 的分數已調整，新的分數為: {player['score']}")
    else:
        await interaction.response.send_message("找不到該用戶，請確認用戶已註冊。")
        
@bot.tree.command(name="調整分數選單版", description="調整指定玩家的分數")
async def adjust_score(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("你沒有權限調整其他用戶的分數。", ephemeral=True)
        return

    # 分頁機制
    page_size = 25
    pages = [players[i:i + page_size] for i in range(0, len(players), page_size)]
    current_page = 0

    def create_user_options(page):
        user_options = []
        for p in page:
            member = interaction.guild.get_member(p['id'])
            if member:
                user_options.append(SelectOption(label=member.display_name, value=str(p['id'])))
            else:
                user_options.append(SelectOption(label=p['name'], value=str(p['id'])))
        return user_options

    # 定義用戶選單
    user_select = Select(
        placeholder="選擇要調整分數的用戶",
        options=create_user_options(pages[current_page]),
        min_values=1,
        max_values=1
    )

    # 定義選單的回調函數
    async def select_callback(interaction: Interaction):
        if not user_select.values:
            await interaction.response.send_message("請選擇一個用戶。", ephemeral=True)
            return

        selected_user_id = int(user_select.values[0])

        # 顯示分數輸入模態
        modal = ScoreInputModal(selected_user_id)
        await interaction.response.send_modal(modal)

    # 定義分頁按鈕的回調函數
    async def change_page(interaction: Interaction, direction: int):
        nonlocal current_page
        current_page += direction
        current_page = max(0, min(current_page, len(pages) - 1))
        user_select.options = create_user_options(pages[current_page])
        await interaction.response.edit_message(view=view)

    # 創建上一頁和下一頁按鈕
    prev_button = Button(label="上一頁", style=discord.ButtonStyle.primary)
    next_button = Button(label="下一頁", style=discord.ButtonStyle.primary)

    prev_button.callback = lambda i: change_page(i, -1)
    next_button.callback = lambda i: change_page(i, 1)

    # 將回調函數綁定到選單
    user_select.callback = select_callback

    # 創建一個視圖並將選單和按鈕添加到視圖中
    view = View()
    view.add_item(user_select)
    view.add_item(prev_button)
    view.add_item(next_button)

    # 發送消息並附加視圖
    await interaction.response.send_message("請選擇用戶並輸入分數變化：", view=view, ephemeral=True)

class ScoreInputModal(Modal):
    def __init__(self, user_id):
        # 查找指定用戶
        player = next((p for p in players if p['id'] == user_id), None)
        super().__init__(title=f"輸入分數變化 (目前分數: {player['score']})")
        self.user_id = user_id
        self.score_input = TextInput(label="分數變化", placeholder="輸入分數變化值", required=True)
        self.add_item(self.score_input)

    async def on_submit(self, interaction: Interaction):
        try:
            score_change = int(self.score_input.value)
        except ValueError:
            await interaction.response.send_message("請輸入有效的數字。", ephemeral=True)
            return

        # 查找指定用戶
        player = next((p for p in players if p['id'] == self.user_id), None)
        if player:
            # 獲取用戶在伺服器中的暱稱
            guild = interaction.guild
            member = guild.get_member(self.user_id)
            nickname = member.display_name if member else player['name']

            # 調整分數
            player['score'] += score_change
            save_players()
            await interaction.response.send_message(f"{nickname} 的分數已調整，新的分數為: {player['score']}", ephemeral=True)
        else:
            await interaction.response.send_message("找不到該用戶，請確認用戶已註冊。", ephemeral=True)
    
# 定義金幣獲得的可能值和其對應的權重
COIN_VALUES = [1, 2, 3, 4, 5]
WEIGHTS = [8, 6, 4, 2, 1]  # 1的機率最高，5的機率最低
@bot.tree.command(name="簽到", description="每日簽到以獲得金幣")
async def daily_check_in(interaction: discord.Interaction):
    # 檢查是否為管理員或在允許的頻道中
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("只有管理員可以使用此指令。", ephemeral=True)
        return

    # 確認用戶是否已註冊
    player = next((p for p in players if p['id'] == interaction.user.id), None)
    
    if not player:
        await interaction.response.send_message("你尚未註冊，請先註冊後再簽到。", ephemeral=True)
        return

    # 確認用戶是否已經簽到過
    last_check_in = player['last_check_in']
    today = datetime.now().date()

    # 將日期轉換為字串格式
    today_str = today.isoformat()

    if last_check_in and last_check_in == today_str:
        await interaction.response.send_message("你今天已經簽到過了，明天再來吧！", ephemeral=True)
        return

    # 隨機選擇獲得的金幣數量
    daily_coins = random.choices(COIN_VALUES, weights=WEIGHTS, k=1)[0]

    # 更新用戶的金幣和最後簽到時間
    player['coins'] += daily_coins
    player['last_check_in'] = today_str

    # 保存更新後的玩家數據
    save_players()

    # 使用者的伺服器暱稱
    display_name = interaction.user.display_name

    # 發送訊息給所有人
    await interaction.response.send_message(f"{display_name} 簽到成功！獲得了 {daily_coins} 金幣。現在有 {player['coins']} 金幣。")

@bot.tree.command(name="贈送金幣", description="將金幣贈送給其他玩家")
async def give_coins(interaction: discord.Interaction, recipient: discord.Member, amount: int):
    # 檢查是否為管理員或在允許的頻道中
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("只有管理員可以使用此指令。", ephemeral=True)
        return

    # 確認贈送者是否已註冊
    sender = next((p for p in players if p['id'] == interaction.user.id), None)
    if not sender:
        await interaction.response.send_message("你尚未註冊，請先註冊後再贈送金幣。", ephemeral=True)
        return

    # 確認接收者是否已註冊
    receiver = next((p for p in players if p['id'] == recipient.id), None)
    if not receiver:
        await interaction.response.send_message("接收者尚未註冊，無法接收金幣。", ephemeral=True)
        return

    # 確認贈送者有足夠的金幣
    if sender['coins'] < amount:
        await interaction.response.send_message("你的金幣不足，無法贈送這麼多金幣。", ephemeral=True)
        return

    # 更新雙方的金幣數量
    sender['coins'] -= amount
    receiver['coins'] += amount

    # 保存更新後的玩家數據
    save_players()

    # 發送確認訊息
    sender_name = interaction.user.display_name
    receiver_name = recipient.display_name
    await interaction.response.send_message(f"{sender_name} 成功贈送 {amount} 金幣給 {receiver_name}！")

@bot.tree.command(name="伺服器狀態", description="查看伺服器的總金幣和總進行場數")
async def server_status(interaction: discord.Interaction):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return

    # 計算總金幣
    total_coins = sum(player['coins'] for player in players)

    # 創建嵌入消息
    embed = Embed(title="伺服器狀態", color=0x00ff00)
    embed.add_field(name="總金幣", value=f"{total_coins}", inline=False)
    embed.add_field(name="總進行場數", value=f"{total_matches_played}", inline=False)
    embed.add_field(name="總玩家數", value=f"{len(players)}", inline=False)

    # 發送嵌入消息
    await interaction.response.send_message(embed=embed, ephemeral=False)
    
AVAILABLE_ROLES = [
    ("世紀富豪 1天 (可移動世紀頻道的人、靜言、拒聽)",1342032524443910164, 10, 1),  # Role1 需要 10 金幣，有效期 1 天
]

class RoleSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=f"{name} - {coins} 金幣",
                value=name
            )
            for name, role , coins, days in AVAILABLE_ROLES
        ]
        super().__init__(placeholder="選擇要購買的身分組", options=options)

    async def callback(self, interaction: discord.Interaction):
        role_name = self.values[0]
        role_info = next((r for r in AVAILABLE_ROLES if r[0] == role_name), None)
        
        if not role_info:
            await interaction.response.send_message('找不到該身分組！', ephemeral=True)
            return

        name,role, required_coins, days = role_info
        role_obj = discord.utils.get(interaction.guild.roles, id=role)
        if role_obj is None:
            await interaction.response.send_message(f'伺服器中找不到角色：{role}。請確認角色名稱是否正確。', ephemeral=True)
            return

        # 檢查玩家是否已註冊
        player = next((p for p in players if p['id'] == interaction.user.id), None)
        if not player:
            await interaction.response.send_message('你尚未註冊。', ephemeral=True)
            return

        # 檢查用戶是否有足夠的金幣
        if player['coins'] < required_coins:
            await interaction.response.send_message('你的金幣不足以購買這個身分組。', ephemeral=True)
            return

        # 扣除金幣並添加角色
        player['coins'] -= required_coins
        expiry_time = datetime.now() + timedelta(days=days)
        if 'roles' not in player:
            player['roles'] ={}
        player['roles'][role] = expiry_time.isoformat()
        save_players()

        await interaction.user.add_roles(role_obj)
        await interaction.response.send_message(f'{interaction.user.display_name} 已購買 {role_name} 身分組！')

@bot.tree.command(name="購買身分組", description="購買自定義身分組並設置期限")
async def buy_role(interaction: discord.Interaction):
    view = View()
    view.add_item(RoleSelect())
    await interaction.response.send_message("請選擇要購買的身分組：", view=view, ephemeral=True)

@bot.tree.command(name="猜拳賭博", description="開始一場猜拳賭博遊戲")
async def start_rock_paper_scissors(interaction: Interaction, bet_amount: int):
    if bet_amount <= 0:
        await interaction.response.send_message("賭注金額必須大於零。", ephemeral=True)
        return

    game_id = generate_unique_game_id()
    games[game_id] = {
        'participants': [],
        'started': False,
        'result_decided': False,
        'bet_amount': bet_amount
    }
    async def join_game_callback(interaction: Interaction):
        user_id = interaction.user.id
        player_info = next((p for p in players if p['id'] == user_id), None)
    
        if not player_info:
            await interaction.response.send_message("你的資料不在系統中，請聯繫管理員。", ephemeral=True)
            return
    
        if player_info['coins'] < bet_amount:
            await interaction.response.send_message("你的金幣不足以參加這場遊戲。", ephemeral=True)
            return
    
        if any(p['id'] == user_id for p in games[game_id]['participants']):
            await interaction.response.send_message("你已經加入了這場遊戲。", ephemeral=True)
            return
    
        # 將玩家添加到參與者列表中
        games[game_id]['participants'].append({
            'id': player_info['id'],
            'userName': player_info['userName'],
            'coins': player_info['coins'],
            'bet_amount': bet_amount
        })

        # 更新參賽者列表
        participant_names = [p['userName'] for p in games[game_id]['participants']]
        participant_list = "\n".join(participant_names)
        # 編輯原始訊息以顯示更新的參賽者名單
        await interaction.message.edit(content=f"遊戲已創建，ID: {game_id}。賭注金額為 {bet_amount} 金幣。\n\n目前參賽者：\n{participant_list}")
        # 更新訊息以顯示參賽者
        await interaction.response.send_message(f"你已加入遊戲，並扣除了賭注金額。\n\n目前參賽者：\n{participant_list}",ephemeral=True)


    async def play_game_callback(interaction: Interaction):
        if games[game_id]['started']:
            await interaction.response.send_message("遊戲已經開始。", ephemeral=True)
            return

        if len(games[game_id]['participants']) < 2:
            await interaction.response.send_message("參加人數不足，無法開始遊戲。", ephemeral=True)
            return

        for participant in games[game_id]['participants']:
            player_info = next((p for p in players if p['id'] == participant['id']), None)
            if player_info:
                player_info['coins'] -= participant['bet_amount']
                update_player_coins(player_info['id'], player_info['coins'])
        games[game_id]['started'] = True
        await interaction.response.send_message("遊戲開始！請選擇你的出拳。", ephemeral=True)

        # 設置猜拳按鈕
        rock_button = Button(label="石頭", style=ButtonStyle.primary)
        paper_button = Button(label="布", style=ButtonStyle.primary)
        scissors_button = Button(label="剪刀", style=ButtonStyle.primary)

        async def rock_callback(interaction: Interaction):
            await process_choice(interaction, "石頭")

        async def paper_callback(interaction: Interaction):
            await process_choice(interaction, "布")

        async def scissors_callback(interaction: Interaction):
            await process_choice(interaction, "剪刀")

        rock_button.callback = rock_callback
        paper_button.callback = paper_callback
        scissors_button.callback = scissors_callback

        choice_view = View()
        choice_view.add_item(rock_button)
        choice_view.add_item(paper_button)
        choice_view.add_item(scissors_button)

        await interaction.followup.send("請選擇你的出拳：", view=choice_view)

    async def process_choice(interaction: Interaction, choice: str):
        user_id = interaction.user.id
        participant = next((p for p in games[game_id]['participants'] if p['id'] == user_id), None)
        if not participant:
            await interaction.response.send_message("你不在這場遊戲中。", ephemeral=True)
            return

        participant['choice'] = choice
        await interaction.response.send_message(f"你選擇了 {choice}。", ephemeral=True)

        # 檢查是否所有玩家都已選擇
        if all('choice' in p for p in games[game_id]['participants']):
            await determine_winner(interaction)

    async def determine_winner(interaction: Interaction):
        choices = [p['choice'] for p in games[game_id]['participants']]
        unique_choices = set(choices)

        if len(unique_choices) == 1:
            result = "平手！"
            # 退還賭注金額
            for player in games[game_id]['participants']:
                player['coins'] += player['bet_amount']
                update_player_coins(player['id'], player['coins'])
        else:
            if "石頭" in unique_choices and "剪刀" in unique_choices:
                result = "石頭勝！"
                winner = "石頭"
            elif "剪刀" in unique_choices and "布" in unique_choices:
                result = "剪刀勝！"
                winner = "剪刀"
            elif "布" in unique_choices and "石頭" in unique_choices:
                result = "布勝！"
                winner = "布"
            else:
                result = "無法決定勝負。"
                winner = None

            if winner:
                winning_players = [p for p in games[game_id]['participants'] if p['choice'] == winner]
                total_bet = sum(p['bet_amount'] for p in games[game_id]['participants'])
                reward = total_bet / len(winning_players)
                for player in winning_players:
                    player['coins'] += reward
                    update_player_coins(player['id'], player['coins'])

        embed = Embed(title="猜拳結果", description=result, color=0x00ff00)
        await interaction.followup.send(embed=embed)
        del games[game_id]

    join_button = Button(label="加入遊戲", style=ButtonStyle.primary)
    play_button = Button(label="開始遊戲", style=ButtonStyle.green)

    join_button.callback = join_game_callback
    play_button.callback = play_game_callback

    view = View()
    view.add_item(join_button)
    view.add_item(play_button)

    await interaction.response.send_message(f'遊戲已創建，ID: {game_id}。賭注金額為 {bet_amount} 金幣。點擊按鈕加入或開始遊戲。', view=view)

def update_player_coins(player_id, new_coins):
    # 假設這個函數會更新玩家的金幣數量到資料庫或資料結構中
    for player in players:
        if player['id'] == player_id:
            player['coins'] = new_coins
            break
            
@bot.tree.command(name="購買臨時頻道", description="購買一個限時頻道")
@app_commands.describe(channel_name="你想創建的頻道名稱", duration="頻道存在的時間（以日為單位 週/1金幣）")
async def buy_temporary_channel(interaction: discord.Interaction, channel_name: str, duration: int):
    # 檢查玩家是否已註冊
    player = next((p for p in players if p['id'] == interaction.user.id), None)
    if not player:
        await interaction.response.send_message("你需要先使用 /註冊 指令註冊。", ephemeral=True)
        return

    # 檢查玩家是否有足夠的 coins
    channel_cost = 1  # 假設創建頻道需要 100 coins
    channel_cost *= duration
    if player['coins'] < channel_cost:
        await interaction.response.send_message("你的 coins 不足以購買頻道。", ephemeral=True)
        return

    # 獲取類別
    category = discord.utils.get(interaction.guild.categories, id=1342061227647696978)
    if not category:
        await interaction.response.send_message("指定的類別不存在。", ephemeral=True)
        return

    # 設置頻道權限
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, manage_channels=True, manage_permissions=True)
    }

    # 創建頻道
    channel = await interaction.guild.create_voice_channel(name=channel_name, category=category, overwrites=overwrites)
    # 計算到期時間
    expiry_time = datetime.now() + timedelta(weeks=duration)
    if 'channels' not in player:
        player['channels'] = {}
    player['channels'][str(channel.id)] = expiry_time.isoformat()

    # 從玩家的 coins 中扣除
    player['coins'] -= channel_cost
    save_players()

    await interaction.response.send_message(f"頻道 '{channel_name}' 已在 {category.name} 下創建，並且你擁有管理權限。該頻道將在 {duration} 週後自動刪除。", ephemeral=True)

@bot.tree.command(name="延長期限", description="延長當前語音頻道的期限")
@app_commands.describe(additional_duration="延長的時間（以週為單位）")
async def extend_channel_duration(interaction: discord.Interaction, additional_duration: int):
    # 獲取當前語音頻道
    if not interaction.channel or not isinstance(interaction.channel, discord.VoiceChannel):
        await interaction.response.send_message("此指令必須在語音頻道的聊天窗口中使用。", ephemeral=True)
        return

    channel_id = str(interaction.channel.id)
    player = next((p for p in players if p['id'] == interaction.user.id), None)
    if not player or 'channels' not in player or channel_id not in player['channels']:
        await interaction.response.send_message("你沒有管理這個頻道或頻道不存在。", ephemeral=True)
        return

    # 計算延長所需的金幣
    extension_cost = additional_duration  # 假設每週需要1金幣
    if player['coins'] < extension_cost:
        await interaction.response.send_message("你的 coins 不足以延長頻道期限。", ephemeral=True)
        return

    # 更新到期時間
    current_expiry = datetime.fromisoformat(player['channels'][channel_id])
    new_expiry = current_expiry + timedelta(weeks=additional_duration)
    player['channels'][channel_id] = new_expiry.isoformat()

    # 扣除金幣
    player['coins'] -= extension_cost
    save_players()

    await interaction.response.send_message(f"頻道的期限已延長至 {new_expiry.strftime('%Y-%m-%d %H:%M:%S')}", ephemeral=True)

# 自動補全道具名稱
async def item_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=item, value=item)
        for item in ITEMS.keys() if current.lower() in item.lower()
    ]

@bot.tree.command(name="購買道具", description="購買道具")
@app_commands.describe(item_name="道具名稱")
@app_commands.autocomplete(item_name=item_autocomplete)
async def buy_item(interaction: discord.Interaction, item_name: str):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return

    # 檢查道具是否存在
    if item_name not in ITEMS:
        await interaction.response.send_message("找不到該道具，請確認道具名稱是否正確。", ephemeral=True)
        return

    # 檢查玩家是否已註冊
    player = next((p for p in players if p['id'] == interaction.user.id), None)
    if not player:
        await interaction.response.send_message("你尚未註冊，請先註冊後再購買道具。", ephemeral=True)
        return

    # 檢查玩家是否有足夠的金幣
    item = ITEMS[item_name]
    if player['coins'] < item['price']:
        await interaction.response.send_message("你的金幣不足以購買這個道具。", ephemeral=True)
        return

    # 初始化 items 字段（如果不存在）
    if 'items' not in player:
        player['items'] = {}

    # 扣除金幣並添加道具
    player['coins'] -= item['price']
    if item_name in player['items']:
        player['items'][item_name] += 1  # 如果已經有該道具，增加數量
    else:
        player['items'][item_name] = 1  # 如果沒有該道具，初始化數量為 1
    save_players()

    await interaction.response.send_message(f"你已成功購買 {item_name}！", ephemeral=True)

@bot.tree.command(name="使用道具", description="在比賽中使用道具")
@app_commands.describe(item_name="道具名稱", game_id="比賽ID")
@app_commands.autocomplete(item_name=item_autocomplete)
async def use_item(interaction: discord.Interaction, item_name: str, game_id: str):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return

    # 檢查道具是否存在
    if item_name not in ITEMS:
        await interaction.response.send_message("找不到該道具，請確認道具名稱是否正確。", ephemeral=True)
        return

    # 檢查玩家是否已註冊
    player = next((p for p in players if p['id'] == interaction.user.id), None)
    if not player:
        await interaction.response.send_message("你尚未註冊，請先註冊後再使用道具。", ephemeral=True)
        return

    # 初始化 items 字段（如果不存在）
    if 'items' not in player:
        player['items'] = {}

    # 檢查玩家是否擁有該道具
    if item_name not in player['items'] or player['items'][item_name] <= 0:
        await interaction.response.send_message("你沒有這個道具。", ephemeral=True)
        return

    # 檢查比賽是否存在
    if game_id not in games:
        await interaction.response.send_message("找不到該比賽，請確認比賽ID是否正確。", ephemeral=True)
        return

    # 檢查比賽是否已經開始
    if games[game_id]['started']:
        await interaction.response.send_message("比賽已經開始，無法使用道具。", ephemeral=True)
        return

    # 檢查是否已經有人使用過道具
    if 'used_items' in games[game_id] and games[game_id]['used_items']:
        await interaction.response.send_message("本場比賽已經有人使用過道具了。", ephemeral=True)
        return

    # 使用道具
    item = ITEMS[item_name]
    games[game_id]['used_items'] = True
    games[game_id]['used_item_by'] = interaction.user.display_name
    games[game_id]['used_item_effect'] = item['effect']

    # 移除道具（減少數量）
    player['items'][item_name] -= 1
    if player['items'][item_name] == 0:
        del player['items'][item_name]  # 如果數量為 0，移除該道具
    save_players()

    await interaction.response.send_message(f"你已成功使用 {item_name}！", ephemeral=True)
    
@bot.tree.command(name="查詢道具", description="查詢你擁有的道具")
async def query_items(interaction: discord.Interaction):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return

    # 檢查玩家是否已註冊
    player = next((p for p in players if p['id'] == interaction.user.id), None)
    if not player:
        await interaction.response.send_message("你尚未註冊，請先註冊後再查詢道具。", ephemeral=True)
        return

    # 初始化 items 字段（如果不存在）
    if 'items' not in player:
        player['items'] = {}

    # 檢查玩家是否擁有道具
    if not player['items']:
        await interaction.response.send_message("你目前沒有道具。", ephemeral=True)
        return

    # 構建道具列表
    items_list = "\n".join([f"{item_name} x {quantity}" for item_name, quantity in player['items'].items()])
    await interaction.response.send_message(f"你擁有的道具：\n{items_list}", ephemeral=True)

@bot.tree.command(name="查詢天氣", description="查詢當前的天氣效果及其對分數增減的影響")
async def query_weather(interaction: discord.Interaction):
    if interaction.channel.id != ALLOWED_CHANNEL_ID and interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("此指令只能在指定的頻道中使用。", ephemeral=True)
        return

    # 獲取當前天氣
    weather = server_info.get('weather', "晴天")  # 默認為晴天
    weather_multiplier = WEATHER_EFFECTS.get(weather, 1.0)  # 默認倍率為 1.0

    # 構建回覆訊息
    response_message = (
        f"**當前天氣：** {weather}\n"
        f"**分數增減倍率：** {weather_multiplier}x\n"
        f"**效果描述：** {get_weather_description(weather)}"
    )

    # 回覆用戶
    await interaction.response.send_message(response_message)

def get_weather_description(weather: str) -> str:
    """根據天氣返回效果描述"""
    descriptions = {
        "晴天": "分數增減幅度正常。",
        "暴風雨": "分數增減幅度增加 50%。",
        "微風": "分數增減幅度減少 20%。",
        "雷電": "分數增減幅度大幅增加 100%。",
        "霧霾": "分數增減幅度隨機波動（0.5x 到 1.5x）。"
    }
    return descriptions.get(weather, "未知天氣效果。")
    
@bot.tree.command(name="help", description="顯示所有可用指令及其描述")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "**可用指令：**\n"
        "/總地圖-新增 <地圖名稱> - 添加地圖到總地圖池\n"
        "/總地圖-移除 <地圖名稱> - 從總地圖池移除地圖\n"
        "/總地圖池-查看 - 查看當前總地圖池\n"
        "/抽圖 - 隨機選擇一個地圖從暫時地圖池\n"
        "/暫時地圖-新增 <地圖名稱> - 添加地圖到暫時地圖池\n"
        "/暫時地圖-移除 <地圖名稱> - 從暫時地圖池移除地圖\n"
        "/暫時地圖-查看 - 查看暫時地圖池\n"
        "/暫時地圖-清空 - 清空暫時地圖池\n"
        "/從總地圖快速新增暫時地圖池 <地圖名稱> - 從總地圖池快速添加地圖到暫時地圖池\n"
        "/快速新增暫時地圖池 <地圖名稱> - 快速新增暫時地圖池\n"
        "/抽 <項目列表> - 從提供的列表中隨機抽取一個項目\n"
        "/計算機 <表達式> - 計算四則運算表達式\n"
        "/創建比賽 - 創建一場新的比賽\n"
        "/查詢分數 - 查詢玩家的分數和穩定性\n"
        "/查詢合作勝率 - 查詢玩家與特定隊友的合作勝率\n"
        "/排行榜 - 查看所有玩家的排行榜\n"
        "/贈送金幣 - 將金幣贈送給其他玩家\n"
        "/簽到 - 每日簽到獲取金幣\n"
        "/投注 - 投注比賽\n"
        "/猜拳賭博 - 猜拳賭博\n"
        "/購買身分組 - 購買身分組\n"
        "/購買臨時頻道 - 買一個臨時頻道 自己有該頻道所有權限\n"
        "/延長期限 - 延長當前語音頻道的期限\n"
        "/購買道具 <道具名稱> - 購買道具\n"
        "/使用道具 <道具名稱> <比賽ID> - 在比賽中使用道具\n"
        "/查詢道具 - 查詢你擁有的道具\n"
        "/查詢天氣 - 查詢目前伺服器天氣\n"
    )
    await interaction.response.send_message(help_text)

# 在這裡替換成你的機器人Token
TOKEN = ''

# 啟動機器人
bot.run(TOKEN)
