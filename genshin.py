import genshinstats as gs
import discord
from discord import ui
from enkanetwork import EnkaNetworkAPI
from discord.ui import View
import aiohttp
import sqlite3
import time


#TOKEN
TOKEN = 'xxxxxx'

intents=discord.Intents.all()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

modal_id = 0
bot_name = ""

conn=sqlite3.connect("./genshin.db", check_same_thread=False)
c=conn.cursor()
data=c.fetchone()
c.execute("CREATE TABLE IF NOT EXISTS genshin(modalid str primary key, selectid str, mapid str, cancelid str, uid int)")

@client.event
async def on_ready():
    global bot_name
    print("èµ·å")
    bot_name=client.user.name
    await client.change_presence(activity=discord.Game(name="ð¥ããããããã±ãã¨"))
    await tree.sync()

#ã¢ã¼ãã«ãããã¢ããã¦ã£ã³ãã¦ã¨ãã¬ã¤ã¤ã¼ã¹ãã¼ã¿ã¹ã®è¡¨ç¤º
class GenshinModal(ui.Modal):
    def __init__(self):
        super().__init__(
            title="åç¥ã®UIDãå¥åãã¦ãã ãã"
        )

        self.contents = ui.TextInput(
            label="UID",
            style= discord.TextStyle.short,
            placeholder="ä¾:847262599",
            required=True,
        )
        self.add_item(self.contents)

    #UIDå¥åå¾ã«ãã¬ã¤ã¤ã¼ã¹ãã¼ã¿ã¹èµ°æ»
    async def on_submit(self, interaction: discord.Interaction):
        global modal_id

        await interaction.response.send_message(content="ã­ã£ã©ã¯ã¿ã¼ã¹ãã¼ã¿ã¹åå¾ä¸­...")
        
        #channel_id=interaction.channel_id
        #channel = await interaction.guild.fetch_channel(channel_id)

        try:
            uid = int(self.contents.value)
        except Exception as e:
            print(e)
            await interaction.edit_original_response(content="å¥åã«ééãããããï¼")
            time.sleep(1.2)
            await interaction.delete_original_response()

            return

        client = EnkaNetworkAPI(lang='jp')

        try:
            async with client:
                data_enka = await client.fetch_user(uid)
        except Exception as e:
            print(e)
            await interaction.edit_original_response(content="ãããªäººããªããï¼")
            time.sleep(1.2)
            await interaction.delete_original_response()
            return


        stats = await player_status(uid,data_enka)
        view = View(timeout=None)

        if stats == None:
            await interaction.edit_original_response(content="éå¬éã¦ã¼ã¶ã ãï¼")
            time.sleep(1.2)
            await interaction.delete_original_response()
            return

        modal_id = self.custom_id
        c.execute("INSERT INTO genshin VALUES(?, ?, ?, ?, ?)",(self.custom_id, "", "" , "", uid))
        conn.commit()

        try:
            view.add_item(enka(data_enka))
        except Exception as e:
            print(e)
            if "DataNotPublic" in str(e.__class__):
                pass
        
        try:
            #HoyoLabã«å¬éãã¦ããäººã¯ãã®æ©è½ãä½¿ã
            gs.set_cookie(ltuid=179694940, ltoken="3DRoaeDyHN1gFhpvhJ8H1VSfVPuwRrD8fwbP6Nll")
            data_hoyo = gs.get_all_user_data(uid,lang="ja-jp")
            view.add_item(hoyo(data_hoyo))
        #ã¨ã©ã¼æ
        except Exception as e:
            print(e)
            if "DataNotPublic" in str(e.__class__):
                pass

        button = HugaButton("æä½çµäº")
        view.add_item(button)

        try:
            #await channel.send(embed=stats,view=view,ephemeral=True)
            await interaction.edit_original_response(content=None,embed=stats,view=view)
            return
        except Exception as e:
            print(e)
            await interaction.edit_original_response(content="éå¬éã¦ã¼ã¶ããã­")
            time.sleep(1.2)
            await interaction.delete_original_response()
            c.execute("DELETE FROM genshin WHERE modalid=?", (modal_id,))
            conn.commit()

            return

class HugaListChara(discord.ui.Select):
    global modal_id
    def __init__(self,args,txt):
        options=[]
        for chara,lv in zip(args.keys(),args.values()):
            options.append(discord.SelectOption(label=chara + " " + str(lv) + "Lv", description=''))
        
        super().__init__(placeholder=txt, min_values=1, max_values=1, options=options)

        try:
            c.execute("UPDATE genshin set selectid =? WHERE modalid =?", (self.custom_id, modal_id))
            conn.commit()
        except Exception as e:
            print(e)
            pass

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="ã­ã£ã©ãã¼ã¿åå¾ä¸­...")

        c.execute("SELECT uid from genshin where selectid=?",(self.custom_id,))
        uid=c.fetchone()[0]

        client = EnkaNetworkAPI(lang='jp')
        async with client:
            data_enka = await client.fetch_user(uid)
        
        #ããããã­ã£ã©ã¯ã¿ã¼ã®ã¹ãã¼ã¿ã¹ãæ ¼ç´ãã
        status = None

        url = f"https://enka.network/u/{uid}/__data.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                resps = await response.json()

        try:
            for chara in data_enka.player.characters_preview:
                if self.values[0] == chara.name + " " + str(chara.level) + "Lv":
                    for i in range(len(resps["avatarInfoList"])):
                        if resps["avatarInfoList"][i]["avatarId"] == int(chara.id):
                            #ã­ã£ã©ã¯ã¿ã¼IDã¨ãã¬ã¤ã¤ã¼ã®UID,Level,Iconã®URL
                            status = await character_status(chara.id,chara.name,chara.level,chara.icon.url,resps["avatarInfoList"][i],data_enka)
                            break
        except Exception as e:
            print(e)
            if "User's data is not public" in str(e.__class__) or "KeyError" in str(e.__class__):
                await interaction.message.edit(content="éå¬éã­ã£ã©ã®ããã­")
                return
        
        #ç·¨éããã®ã¯embedã®ã¿ã§ãã£ã¦ï¼ãã¿ã³ãã»ã¬ã¯ãã¡ãã¥ã¼ã¯ç·¨éããªã
        await interaction.message.edit(content=None,embed=status)
        return
    

class HugaListMap(discord.ui.Select):
    global modal_id
    def __init__(self,args,txt):
        options=[]
        for item in args:
            options.append(discord.SelectOption(label=item, description=''))
    
        super().__init__(placeholder=txt, min_values=1, max_values=1, options=options)

        try:
            c.execute("UPDATE genshin set mapid =? WHERE modalid =?", (self.custom_id, modal_id))
            conn.commit()
        except Exception as e:
            print(e)
            pass


    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="ããããã¼ã¿åå¾ä¸­")
        #HoyoLabã«å¬éãã¦ããªãã¦ã¼ã¶ã¯ä½¿ç¨ã§ããªã
        c.execute("SELECT uid from genshin where mapid=?",(self.custom_id,))
        uid=c.fetchone()[0]
        

        gs.set_cookie(ltuid=179694940, ltoken="3DRoaeDyHN1gFhpvhJ8H1VSfVPuwRrD8fwbP6Nll")
        data_hoyo = gs.get_all_user_data(uid,lang="ja-jp")
        for i in range(len(data_hoyo['explorations'])):
            if self.values[0] == data_hoyo["explorations"][i]['name']:
                status = data_hoyo["explorations"][i]
                status = map_status(status)
                break
        #print(status)

        #ç·¨éããã®ã¯embedã®ã¿ã§ãã£ã¦ï¼ãã¿ã³ãã»ã¬ã¯ãã¡ãã¥ã¼ã¯ç·¨éããªã
        await interaction.message.edit(content=None,embed=status)
        return


#æä½çµäºãã¿ã³ã®å®è£
class HugaButton(discord.ui.Button): #HugaButtonã¯Buttonã®ãµãã¯ã©ã¹
    global modal_id
    def __init__(self,txt:str):
        super().__init__(label=txt,style=discord.ButtonStyle.red)
        try:
            c.execute("UPDATE genshin set cancelid =? WHERE modalid =?", (self.custom_id, modal_id))
            conn.commit()
        except Exception as e:
            print(e)
            pass
    
    #async def on_timeout(self):
    #    c.execute("DELETE FROM genshin WHERE cancelid=?", (self.custom_id,))
    #    conn.commit()
    #    await interaction.message.delete()
    #    return

    async def on_error(self,interaction: discord.Interaction):
        print("On_error")
        c.execute("DELETE FROM genshin WHERE cancelid=?", (self.custom_id,))
        conn.commit()
        await interaction.message.delete()
        return

    async def callback(self, interaction: discord.Interaction):
        print("callback_delete")
        c.execute("DELETE FROM genshin WHERE cancelid=?", (self.custom_id,))
        conn.commit()
        await interaction.message.delete()
        #print("test")
        return


@tree.command(
    name="status",#ã³ãã³ãå
    description="åç¥ã®uidãå¥åãã"#ã³ãã³ãã®èª¬æ
)
async def uid(interaction: discord.Interaction):
    genshinModal = GenshinModal()
    await interaction.response.send_modal(genshinModal)


@tree.command(
    name="help",#ã³ãã³ãå
    description="ä½¿ãæ¹ã¨ãããã§é²è¦§ã§ãããã®ãè¦ã"#ã³ãã³ãã®èª¬æ
)
async def help(interaction: discord.Interaction):
    global bot_name
    embed = discord.Embed( 
                        title=bot_name,
                        color=0x1e90ff,
                        description=f"ä½¿ãæ¹ã¨ç§ã§è¦ãããã®ãåããã!"
    )
    embed.add_field(name="`/status`",value="ãã¬ã¤ã¤ã¼ã®ææã­ã£ã©ã¯ã¿ã¼ã¨ãããã®æ¢ç´¢åº¦ãè¦ããã!\nâ»ãã¬ã¤ã¤ã¼ã®ææã­ã£ã©ã¯ã¿ã¼æå ±ãé²è¦§ããã«ã¯ã²ã¼ã ããã­ã£ã©ãè©³ç´°è¡¨ç¤ºãã¦ã­\nâ»ãããæå ±ãè¦ãããã«ã¯HoyoLabã§ãã¬ã¤ã¤ã¼ãã¼ã¿ãå¬éãã¦ã­")
    embed.set_image(url="https://tfansite.jp/img/top/genshin/logo.png")
    await interaction.response.send_message(embed=embed)
    return


def enka(data_enka):
        chara_names = {}
        for chara in data_enka.player.characters_preview:
            chara_names[chara.name] = chara.level

        select = HugaListChara(chara_names,txt="ææã­ã£ã©ã¯ã¿ã¼")
        #view.add_item(select)
        return select

def hoyo(data_hoyo):
    #HoyoLabã«å¬éãã¦ããäººã¯ãã®æ©è½ãä½¿ã
    map_names = []
    for i in range(len(data_hoyo['explorations'])):
        map_names.append(data_hoyo['explorations'][i]['name'])

    #await channel.send(embed=stats,view=view)
    #HoyoLabã«å¬éãã¦ããäººã®ã¿ä½¿ããæ©è½

    select = HugaListMap(map_names,txt="ããã")
    return select

async def player_status(uid,data_enka):
        url = f"https://enka.network/u/{uid}/"
        private = 0

        try:
            embed = discord.Embed( 
                        title=f"{data_enka.player.nickname}ã®åç¥ã¹ãã¼ã¿ã¹",
                        color=0x1e90ff,
                        description=f"uid: {uid}",
                        url=url
            )   
            icon_url = data_enka.player.icon.url.url
            embed.set_thumbnail(url=icon_url)
        except Exception as e:
            print(e)
            return None

        try:
            embed.add_field(inline=False,name="åéºã©ã³ã¯",value=data_enka.player.level)
            embed.add_field(inline=False,name="ä¸çã©ã³ã¯",value=data_enka.player.world_level)
            #embed.add_field(inline=False,name="ã¹ãã¼ã¿ã¹ã¡ãã»ã¼ã¸",value=data_enka.player.signature)
            embed.add_field(inline=False,name="ã¢ãã¼ãã¡ã³ã",value=data_enka.player.achievement)
            embed.add_field(inline=False,name="æ·±é¡èºæ",value=str(data_enka.player.abyss_floor) + "-" + str(data_enka.player.abyss_room))

        except Exception as e:
            print(e)
            if "DataNotPublic" in str(e.__class__):
                private += 1
            elif "DataNotPublic" not in str(e.__class__):
                embed = discord.Embed( 
                        title=f"ãã?ã¨ã©ã¼ãçºçããã...ãã°ãããã¦ããããä¸åãã£ã¦ã­",
                        color=0x1e90ff, 
                        url=url 
                )
                return embed
        
        try:
            gs.set_cookie(ltuid=179694940, ltoken="3DRoaeDyHN1gFhpvhJ8H1VSfVPuwRrD8fwbP6Nll")
            data_hoyo = gs.get_all_user_data(uid,lang="ja-jp")
            embed.add_field(inline=False,name="ã­ã£ã©ä¿ææ°",value=data_hoyo['stats']['characters'])
            embed.add_field(inline=False,name="æ®éã®å®ç®±éæ¾æ°",value=data_hoyo['stats']['common_chests'])
            embed.add_field(inline=False,name="è¯ãå®ç®±éæ¾æ°",value=data_hoyo['stats']['exquisite_chests'])
            embed.add_field(inline=False,name="è±ªè¯ãªå®ç®±éæ¾æ°",value=data_hoyo['stats']['luxurious_chests'])
            embed.add_field(inline=False,name="ãã¬ã¤æ¥æ°",value=data_hoyo["stats"]['active_days'])
        except Exception as e:
            print(e)
            if "DataNotPublic" in str(e.__class__):
                private += 1
            elif "DataNotPublic" not in str(e.__class__):
                embed = discord.Embed( 
                        title=f"ãã?ã¨ã©ã¼ãçºçããã...ãã°ãããã¦ããããä¸åãã£ã¦ã­",
                        color=0x1e90ff, 
                        url=url 
                )
                return embed

        if private < 2:
            return embed
        else:
            return None
#mapã®ã¹ãã¼ã¿ã¹ã®UIãä½ãé¢æ°(embed)
def map_status(status):
    #mapæå ±ã¯enka.Netããåéåºæ¥ããèª¿ã¹ã
    embed = discord.Embed(title=status['name']+'ã®æ¢ç´¢åº¦',description=str(status['explored']) + '%')
    embed.set_image(url=status['icon'])
    return embed


#ã­ã£ã©ã¯ã¿ã¼ã¹ãã¼ã¿ã¹ã®UIãä½ãé¢æ°(embed)
async def character_status(id,name,level,chara_url,resp,data_enka):
    global uid
    embed = discord.Embed(
        title=data_enka.player.nickname + "ããã®" + name,
        color=0x1e90ff, 
        description=f"{level}lv", 
        )
    
    embed.set_thumbnail(url=chara_url)
    embed.add_field(inline=True,name="ã­ã£ã©ã¬ãã«",value=f"{level}lv")
    embed.add_field(inline=True,name="ã­ã£ã©çªç ´ã¬ãã«",value=str(resp["propMap"]["1002"]["ival"]))
    embed.add_field(inline=True,name="HP",
        value=f'{str(round(resp["fightPropMap"]["1"]))} + {str(round(resp["fightPropMap"]["2000"]) - round(resp["fightPropMap"]["1"]))} = {str(round(resp["fightPropMap"]["2000"]))}'
    )
    embed.add_field(inline=True,name="æ»æå",
        value=f'{str(round(resp["fightPropMap"]["4"]))} + {str(round(resp["fightPropMap"]["2001"]) - round(resp["fightPropMap"]["4"]))} = {str(round(resp["fightPropMap"]["2001"]))}'
    )
    embed.add_field(inline=True,name="é²å¾¡å",
        value=f'{str(round(resp["fightPropMap"]["7"]))} + {str(round(resp["fightPropMap"]["2002"]) - round(resp["fightPropMap"]["7"]))} = {str(round(resp["fightPropMap"]["2002"]))}'
    )
    embed.add_field(inline=True,name="ä¼å¿ç",
        value=f'{str(round(resp["fightPropMap"]["20"] *100))}%'
    )
    embed.add_field(inline=True,name="ä¼å¿ãã¡ã¼ã¸",
        value=f'{str(round(resp["fightPropMap"]["22"]*100))}%'
    )
    embed.add_field(inline=True,name="åç´ ãã£ã¼ã¸å¹ç",
        value=f'{str(round(resp["fightPropMap"]["23"]*100))}%'
    )
    embed.add_field(inline=True,name="åç´ çç¥",
        value=f'{str(round(resp["fightPropMap"]["28"]))}'
    )
    
    buf = 1
    if round(resp["fightPropMap"]["30"]*100) > 0:
        embed.add_field(inline=True,name="ç©çãã¡ã¼ã¸",
            value=f'{str(round(resp["fightPropMap"]["30"]*100))}%'
        )
        buf += round(resp["fightPropMap"]["30"])
    elif round(resp["fightPropMap"]["40"]*100) > 0:
        embed.add_field(inline=True,name="çåç´ ãã¡ã¼ã¸",
            value=f'{str(round(resp["fightPropMap"]["40"]*100))}%'
        )
        buf += round(resp["fightPropMap"]["40"])
    elif round(resp["fightPropMap"]["41"]*100) > 0:
        embed.add_field(inline=True,name="é·åç´ ãã¡ã¼ã¸",
            value=f'{str(round(resp["fightPropMap"]["41"]*100))}%'
        )
        buf += round(resp["fightPropMap"]["41"])
    elif round(resp["fightPropMap"]["42"]*100) > 0:
        embed.add_field(inline=True,name="æ°´åç´ ãã¡ã¼ã¸",
            value=f'{str(round(resp["fightPropMap"]["42"]*100))}%'
        )
        buf += round(resp["fightPropMap"]["42"])
    elif round(resp["fightPropMap"]["43"]*100) > 0:
        embed.add_field(inline=True,name="èåç´ ãã¡ã¼ã¸",
            value=f'{str(round(resp["fightPropMap"]["43"]*100))}%'
        )
        buf += round(resp["fightPropMap"]["42"])
    elif round(resp["fightPropMap"]["44"]*100) > 0:
        embed.add_field(inline=True,name="é¢¨åç´ ãã¡ã¼ã¸",
            value=f'{str(round(resp["fightPropMap"]["44"]*100))}%'
        )
        buf += round(resp["fightPropMap"]["44"])
    elif round(resp["fightPropMap"]["45"]*100) > 0:
        embed.add_field(inline=True,name="å²©åç´ ãã¡ã¼ã¸",
            value=f'{str(round(resp["fightPropMap"]["45"]*100))}%'
        )
        buf += round(resp["fightPropMap"]["45"])
    elif round(resp["fightPropMap"]["46"]*100) > 0:
        embed.add_field(inline=True,name="æ°·åç´ ãã¡ã¼ã¸",
            value=f'{str(round(resp["fightPropMap"]["46"]*100))}%'
        )
        buf += round(resp["fightPropMap"]["46"])

    temp = []
    for myvalue in resp["skillLevelMap"].values():
        temp.append(f"{myvalue}")
    embed.add_field(inline=False,name="å¤©è³¦ã¬ãã«",
        value="\n".join(temp)
    )

    for chara in data_enka.characters:
        if str(chara.id) == id:
            for equipment in chara.equipments:
                #èéºç©
                equip_name=()
                level = ""
                stat = ()
                stat_sub=[]
                #print("Flower" in equipment.detail.artifact_type)
                if "Flower" in str(equipment.detail.artifact_type):
                    equip_name= "è±",equipment.detail.name

                if "Feather" in str(equipment.detail.artifact_type):
                    equip_name="ç¾½",equipment.detail.name

                if "Sands" in str(equipment.detail.artifact_type):
                    equip_name="æè¨",equipment.detail.name

                if "Goblet" in str(equipment.detail.artifact_type):
                    equip_name="ã³ãã",equipment.detail.name

                if "Circlet" in str(equipment.detail.artifact_type):
                    equip_name="é ­",equipment.detail.name

                if "Unknown" in str(equipment.detail.artifact_type):
                    equip_name="æ­¦å¨",equipment.detail.name


                level = str(equipment.level)

                if "NUMBER" in str(equipment.detail.mainstats.type):
                    stat=equipment.detail.mainstats.name,str(equipment.detail.mainstats.value)
                    
                if "PERCENT" in str(equipment.detail.mainstats.type):
                    stat=equipment.detail.mainstats.name,str(equipment.detail.mainstats.value) + "%"
                
                
                for sub in equipment.detail.substats:
                    name_=""
                    value_=""
                    if "NUMBER" in str(sub.type):
                        name_=sub.name
                        value_=str(sub.value)
                    if "PERCENT" in str(sub.type):
                        name_=sub.name
                        value_=str(sub.value) + "%"

                    stat_sub.append(f"{name_}ï¼{value_}")
                #print("===========")
                #print()
                
                embed.add_field(inline=True,name='èéºç©ï¼'+ str(equip_name[0])+'\n'+ str(equip_name[1])+'\n'+ str(stat[0])+'ï¼'+str(stat[1])+'\n'+ level+'lv'+'\n',value="\n".join(stat_sub))
            break

    return embed

client.run(TOKEN) #ãããã®ãã¼ã¯ã³