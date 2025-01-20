# Write by GPT & Xiang
import discord
from discord.ext import commands
from discord import app_commands
from discord import Embed
from discord.ui import Button, View
import random
import json
import os

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

# 讀取玩家數據
def load_players():
    if os.path.exists(PLAYERS_FILE):
        with open(PLAYERS_FILE, 'r') as file:
            return json.load(file)
    return []

# 寫入玩家數據
def save_players():
    try:
        with open(PLAYERS_FILE, 'w') as file:
            json.dump(players, file, indent=2)
        print("玩家数据已保存。")  # 添加调试信息
    except Exception as e:
        print(f"保存玩家数据时发生错误: {e}")
		
# 註冊玩家
def register_player(user_id, score, stability):
    players.append({'id': user_id, 'score': score, 'stability': stability})
    save_players()
	


# 分隊邏輯
def balance_teams(participants):
    participants.sort(key=lambda x: x['score'], reverse=True)

    team1 = []
    team2 = []
    score1 = 0
    score2 = 0

    for player in participants:
        if score1 <= score2:
            team1.append(player)
            score1 += player['score']
        else:
            team2.append(player)
            score2 += player['score']

    return team1, team2

# 玩家列表
players = load_players()

# 管理多場比賽的字典
games = {}

# 同步斜線指令
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print("An error occurred while syncing: ", e)

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
async def register(interaction: discord.Interaction, user: discord.User, score: int, stability: float):
    if interaction.user.id != 584371520395149312:
        await interaction.response.send_message("你沒有權限註冊其他用戶。", ephemeral=True)
        return

    # 检查玩家是否已经注册
    if any(p['id'] == user.id for p in players):
        await interaction.response.send_message(f"{user.name} 已經註冊。", ephemeral=True)
        return

    # 注册玩家
    register_player(user.id, score, stability)
    await interaction.response.send_message(f'{user.name} 已註冊，分數: {score}, 穩定度: {stability}')

@bot.tree.command(name="指定加入比賽", description="指定加入比賽")
@app_commands.describe(room_id="比賽房間號", user_mentions="要加入比賽的用戶，使用@標記並用逗號分隔")
async def assign_to_game(interaction: discord.Interaction, room_id: int, user_mentions: str):
    # 檢查是否為管理員
    if interaction.user.id != 584371520395149312:
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
        games[str(room_id)]['participants'].append({'id': user.id, 'score': player_info['score'], 'stability': player_info['stability']})
        response_messages.append(f"<@{user.id}> 已被指定加入房間 {room_id}。")

    # 發送回應訊息
    await interaction.response.send_message("\n".join(response_messages), ephemeral=True)



@bot.tree.command(name="調整分數", description="調整指定玩家的分數")
@app_commands.describe(user="要調整分數的用戶", score_change="分數變化（可以是正數或負數）")
async def adjust_score(interaction: discord.Interaction, user: discord.User, score_change: int):
    # 檢查是否是特定用戶進行的調整
    if interaction.user.id != 584371520395149312:
        await interaction.response.send_message("你沒有權限調整其他用戶的分數。", ephemeral=True)
        return

    # 查找指定用戶
    player = next((p for p in players if p['id'] == user.id), None)
    if player:
        # 調整分數
        player['score'] += score_change
        save_players()
        await interaction.response.send_message(f"{user.name} 的分數已調整，新的分數為: {player['score']}")
    else:
        await interaction.response.send_message("找不到該用戶，請確認用戶已註冊。")
		
@bot.tree.command(name="創建比賽", description="創建一場新的比賽")
async def create_game(interaction: discord.Interaction):
    game_id = str(random.randint(1000, 9999))
    games[game_id] = {'participants': [], 'started': False}

    view = View()
    join_button = Button(label="加入比賽", style=discord.ButtonStyle.primary)
    cancel_button = Button(label="取消參加", style=discord.ButtonStyle.danger)

    async def update_participant_list():
        participants = games[game_id]['participants']
        participant_list = '\n'.join([f"<@{p['id']}> 分數: {p['score']} 穩定性: {p['stability']}" for p in participants]) or "目前無人參加"
        embed = Embed(title=f"房間 {game_id} 參加者名單", description=participant_list, color=0x00ff00)
        await interaction.edit_original_response(embed=embed, view=view)

    async def join_game_callback(interaction):
        user_id = interaction.user.id

        # 檢查房間是否已滿
        if len(games[game_id]['participants']) >= 8:
            await interaction.response.send_message("房間已滿，無法加入。", ephemeral=True)
            return

        # 檢查玩家是否已經加入比賽
        if any(p['id'] == user_id for p in games[game_id]['participants']):
            await interaction.response.send_message("你已經加入了這場比賽。", ephemeral=True)
            return

        # 檢查玩家是否已註冊
        player_info = next((p for p in players if p['id'] == user_id), None)
        if not player_info:
            await interaction.response.send_message("你的資料不在系統中，請聯繫管理員。", ephemeral=True)
            return

        # 添加玩家到比賽
        games[game_id]['participants'].append({'id': user_id, 'score': player_info['score'], 'stability': player_info['stability']})
        await update_participant_list()
        await interaction.response.send_message("加入了這場比賽。", ephemeral=True)

    async def cancel_game_callback(interaction):
        user_id = interaction.user.id
        games[game_id]['participants'] = [p for p in games[game_id]['participants'] if p['id'] != user_id]
        await update_participant_list()
        await interaction.response.send_message("離開了這場比賽。", ephemeral=True)

    join_button.callback = join_game_callback
    cancel_button.callback = cancel_game_callback
    view.add_item(join_button)
    view.add_item(cancel_button)
    start_button = Button(label="開始比賽", style=discord.ButtonStyle.green)
    result_view = View()
    async def start_game_callback(interaction):
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
    
            # 將 team1 和 team2 存儲在 games 中，以便在其他回調中使用
            games[game_id]['team1'] = team1
            games[game_id]['team2'] = team2
    
            team1_info = '\n'.join([f"<@{p['id']}> 分數: {p['score']} 穩定性: {p['stability']}" for p in team1])
            team2_info = '\n'.join([f"<@{p['id']}> 分數: {p['score']} 穩定性: {p['stability']}" for p in team2])
    
            result_view = View()
            button1 = Button(label="Team 1 勝利", style=discord.ButtonStyle.green)
            button2 = Button(label="Team 2 勝利", style=discord.ButtonStyle.red)
    
            button1.callback = button1_callback
            button2.callback = button2_callback
    
            result_view.add_item(button1)
            result_view.add_item(button2)
    
            embed = Embed(title=f"房間 {game_id} 開始！", description=f"**Team 1:**\n{team1_info}\n\n**Team 2:**\n{team2_info}", color=0x00ff00)
            await interaction.response.send_message(embed=embed, view=result_view)
        except Exception as e:
            await interaction.response.send_message(f"發生錯誤: {str(e)}", ephemeral=True)
    
    async def button1_callback(interaction):
        try:
            if games[game_id]['started'] == "team1_won":
                await interaction.response.send_message("比賽已經結束，無法再評判。", ephemeral=True)
                return
    
            games[game_id]['started'] = "team1_won"
            team1 = games[game_id]['team1']
            team2 = games[game_id]['team2']
    
            adjust_scores(team1, team2)
    
            # 生成更新後的統計信息
            updated_stats_info = '\n'.join(
                [f"<@{p['id']}> 分數: {p['score']}, 穩定度: {p['stability']}" for p in team1 + team2]
            )
            embed = Embed(
                title=f"房間 {game_id} 結束！",
                description=f"**Team 1 勝利！**\n\n**更新後的分數與穩定度變動:**\n{updated_stats_info}",
                color=0x00ff00
            )
            await interaction.edit_original_response(embed=embed, view=result_view)
            del games[game_id]
        except discord.errors.NotFound:
            print("交互已过期，无法响应。")
        except Exception as e:
            print(f"发生错误: {str(e)}")
      
		
    async def button2_callback(interaction):
        try:
            if games[game_id]['started'] == "team2_won":
                await interaction.response.send_message("比賽已經結束，無法再評判。", ephemeral=True)
                return
    
            games[game_id]['started'] = "team2_won"
            team1 = games[game_id]['team1']
            team2 = games[game_id]['team2']
    
            adjust_scores(team2, team1)
    
            # 生成更新後的統計信息
            updated_stats_info = '\n'.join(
                [f"<@{p['id']}> 分數: {p['score']}, 穩定度: {p['stability']}" for p in team1 + team2]
            )
            embed = Embed(
                title=f"房間 {game_id} 結束！",
                description=f"**Team 2 勝利！**\n\n**更新後的分數與穩定度變動:**\n{updated_stats_info}",
                color=0x00ff00
            )
            # 先响应交互
            await interaction.response.defer()
            
            # 然后编辑原始响应
            await interaction.edit_original_response(embed=embed, view=result_view)
            del games[game_id]
        except discord.errors.NotFound:
            print("交互已过期，无法响应。")
        except Exception as e:
            print(f"发生错误: {str(e)}")
	    
	    
    start_button.callback = start_game_callback
    view.add_item(start_button)
	
    await interaction.response.send_message(f'房間已創建，ID: {game_id}。點擊按鈕加入或取消參加比賽。', view=view)
    await update_participant_list()

def adjust_scores(winning_team, losing_team):
    # 计算所有玩家的平均分数
    all_players = winning_team + losing_team
    average_score = sum(player['score'] for player in all_players) / len(all_players)

    base_score_increase = 20
    base_score_decrease = 19

    for player in winning_team:
        # 确保稳定度不为负数
        stability = max(1.0, player['stability'])

        # 根据与平均分的差距调整增益
        score_difference = player['score'] - average_score
        score_increase = base_score_increase * (1 - score_difference / average_score)
        # 稳定度影响增益的浮动
        score_increase *= (1 + stability / 10)
        player['score'] += max(1, min(30, score_increase))  # 确保增益在1到30之间
        # 更新稳定度
        player['stability'] = min(10, player['stability'] + 1)
        # 同步更新 players 数组
        for p in players:
            if p['id'] == player['id']:
                p['score'] = player['score']
                p['stability'] = player['stability']
                break

    for player in losing_team:
        # 确保稳定度不为负数
        stability = max(1.0, player['stability'])

        # 根据与平均分的差距调整减少
        score_difference = player['score'] - average_score
        score_decrease = base_score_decrease * (1 + score_difference / average_score)
        # 稳定度影响减少的浮动
        score_decrease *= (1 + stability / 10)
        player['score'] -= max(1, min(30, score_decrease))  # 确保减少在1到30之间
        # 更新稳定度
        player['stability'] = max(0, player['stability'] - 1)
        # 同步更新 players 数组
        for p in players:
            if p['id'] == player['id']:
                p['score'] = player['score']
                p['stability'] = player['stability']
                break

    save_players()

def balance_teams(participants):
    # 簡單的分隊邏輯，這裡可以根據實際需求調整
    half = len(participants) // 2
    return participants[:half], participants[half:]

@bot.tree.command(name="查詢分數", description="查詢玩家的分數和穩定性")
async def query_score(interaction: discord.Interaction, user: discord.User):
    player = next((p for p in players if p['id'] == user.id), None)
    if player:
        embed = Embed(title=f"{user.name} 的資訊", description=f"分數: {player['score']}\n穩定性: {player['stability']}", color=0x00ff00)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("找不到該用戶，請確認用戶已註冊。")
	
# 添加地圖到總地圖池
@bot.tree.command(name="總地圖-新增", description="添加地圖到總地圖池")
@app_commands.describe(map_name="地圖名稱")
async def add_map(interaction: discord.Interaction, map_name: str):
    guild_id = str(interaction.guild_id)
    if guild_id not in map_pools:
        map_pools[guild_id] = []
    map_pools[guild_id].append(map_name)
    save_map_pools()
    await interaction.response.send_message(f"地圖 '{map_name}' 已添加到總地圖池！")

# 從總地圖池移除地圖
@bot.tree.command(name="總地圖-移除", description="從總地圖池移除地圖")
@app_commands.describe(map_name="地圖名稱")
async def remove_map(interaction: discord.Interaction, map_name: str):
    guild_id = str(interaction.guild_id)
    if guild_id in map_pools and map_name in map_pools[guild_id]:
        map_pools[guild_id].remove(map_name)
        save_map_pools()
        await interaction.response.send_message(f"地圖 '{map_name}' 已從總地圖池移除！")
    else:
        await interaction.response.send_message(f"地圖 '{map_name}' 不在總地圖池中！")

# 查看當前總地圖池
@bot.tree.command(name="總地圖池-查看", description="查看當前總地圖池")
async def view_maps(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    if guild_id in map_pools and map_pools[guild_id]:
        maps_list = ', '.join(map_pools[guild_id])
        await interaction.response.send_message(f"當前總地圖池：{maps_list}")
    else:
        await interaction.response.send_message("總地圖池目前是空的！")

# 隨機選擇地圖從暫時地圖池
@bot.tree.command(name="抽圖", description="隨機選擇一個地圖從暫時地圖池")
async def roll_map(interaction: discord.Interaction):
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
    guild_id = str(interaction.guild_id)
    if guild_id not in temp_map_pools:
        temp_map_pools[guild_id] = []
    temp_map_pools[guild_id].append(map_name)
    await interaction.response.send_message(f"地圖 '{map_name}' 已添加到暫時地圖池！")

# 從暫時地圖池移除地圖
@bot.tree.command(name="暫時地圖-移除", description="從暫時地圖池移除地圖")
@app_commands.describe(map_name="地圖名稱")
async def remove_temp_map(interaction: discord.Interaction, map_name: str):
    guild_id = str(interaction.guild_id)
    if guild_id in temp_map_pools and map_name in temp_map_pools[guild_id]:
        temp_map_pools[guild_id].remove(map_name)
        await interaction.response.send_message(f"地圖 '{map_name}' 已從暫時地圖池移除！")
    else:
        await interaction.response.send_message(f"地圖 '{map_name}' 不在暫時地圖池中！")

# 查看暫時地圖池
@bot.tree.command(name="暫時地圖-查看", description="查看暫時地圖池")
async def view_temp_maps(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    if guild_id in temp_map_pools and temp_map_pools[guild_id]:
        maps_list = ', '.join(temp_map_pools[guild_id])
        await interaction.response.send_message(f"暫時地圖池：{maps_list}")
    else:
        await interaction.response.send_message("暫時地圖池目前是空的！")

# 清空暫時地圖池
@bot.tree.command(name="暫時地圖-清空", description="清空暫時地圖池")
async def clear_temp_map(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    temp_map_pools[guild_id] = []
    await interaction.response.send_message("暫時地圖池已清空！")

# 從總地圖池快速添加地圖到暫時地圖池
@bot.tree.command(name="從總地圖快速新增暫時地圖池", description="從總地圖池快速添加地圖到暫時地圖池")
@app_commands.describe(map_names="地圖名稱（用逗號分隔）")
async def quick_add_temp_map(interaction: discord.Interaction, map_names: str):
    guild_id = str(interaction.guild_id)
    if guild_id not in temp_map_pools:
        temp_map_pools[guild_id] = []
    map_list = map_names.split(',')
    added_maps = []
    for map_name in map_list:
        map_name = map_name.strip()
        if map_name in map_pools.get(guild_id, []):
            temp_map_pools[guild_id].append(map_name)
            added_maps.append(map_name)
    if added_maps:
        await interaction.response.send_message(f"地圖 {', '.join(added_maps)} 已從總地圖池快速添加到暫時地圖池！")
    else:
        await interaction.response.send_message("沒有地圖被添加，請確認地圖名稱是否正確！")

@bot.tree.command(name="快速新增暫時地圖池", description="快速新增暫時地圖池")
@app_commands.describe(map_names="地圖名稱（用逗號分隔）")
async def quick_add_temp_map(interaction: discord.Interaction, map_names: str):
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
    )
    await interaction.response.send_message(help_text)

# 在這裡替換成你的機器人Token
TOKEN = ''

# 啟動機器人
bot.run(TOKEN)
