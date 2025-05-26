import discord
from discord.ext import commands, tasks
import datetime
from collections import defaultdict
import asyncio
import re
import emoji
import os

# Token do bot
bot.run(TOKEN)

# Nomes dos canais
CANAL_ORIGEM_NOME = 'edificar'
CANAL_DESTINO_NOME = 'edificação'

# Nome do cargo
CARGO_AUTORIZADO = "sacerbot"

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True
intents.guild_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Tópicos e perguntas
TOPICOS_PERGUNTAS = {
    "Oração": "Pelo que você tem orado esses dias?",
    "Dificuldade": "Quais têm sido suas dificuldades relacionadas à fé?",
    "Comunhão": "Como tem sido sua comunhão com os irmãos?",
    "Bíblico": "Qual versículo ou passagem bíblica te edificou recentemente?"
}

respostas_por_usuario = defaultdict(lambda: defaultdict(str))
mensagens_perguntas = defaultdict(dict)
servidor_alvo = {}

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} está online!")
    lembrete_quinta.start()
    limpar_threads_quinta.start()

@tasks.loop(minutes=1)
async def lembrete_quinta():
    agora_utc = datetime.datetime.now(datetime.timezone.utc)
    agora = agora_utc - datetime.timedelta(hours=3)  # UTC-3
    if agora.weekday() == 3 and agora.hour in [10, 20] and agora.minute == 0:
        for guild in bot.guilds:
            cargo = discord.utils.get(guild.roles, name=CARGO_AUTORIZADO)
            if cargo:
                for member in guild.members:
                    if member != bot.user and CARGO_AUTORIZADO in [role.name for role in member.roles]:
                        try:
                            print(f"Tentando enviar DM para {member.display_name} (ID: {member.id}) em {guild.name}")
                            for topico, pergunta in TOPICOS_PERGUNTAS.items():
                                mensagem = await member.send(pergunta)
                                mensagens_perguntas[member.id][mensagem.id] = topico
                                await asyncio.sleep(1)
                            servidor_alvo[member.id] = guild.id
                            print(f"[{agora}] Perguntas enviadas no privado para {member.display_name} (Servidor: {guild.name})")
                        except Exception as e:
                            print(f"Erro ao enviar perguntas para {member.display_name} em '{guild.name}': {e}")
            else:
                print(f"Cargo '{CARGO_AUTORIZADO}' não encontrado no servidor '{guild.name}'")
                owner = guild.owner
                if owner:
                    await owner.send(f"Cargo '{CARGO_AUTORIZADO}' não encontrado no servidor '{guild.name}'.")

@tasks.loop(minutes=1)
async def limpar_threads_quinta():
    agora_utc = datetime.datetime.now(datetime.timezone.utc)
    agora = agora_utc - datetime.timedelta(hours=3)  # UTC-3
    if agora.weekday() == 3 and agora.hour == 21 and agora.minute == 0:
        for guild in bot.guilds:
            try:
                respostas_por_usuario.clear()
                mensagens_perguntas.clear()
                servidor_alvo.clear()
                print(f"[{agora}] Dicionário de respostas, perguntas e servidores alvo limpo para '{guild.name}'")
            except Exception as e:
                print(f"Erro ao limpar dicionário em '{guild.name}': {e}")
                owner = guild.owner
                if owner:
                    await owner.send(f"Erro ao limpar dicionário no servidor '{guild.name}': {e}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        try:
            content = message.content.strip()
            if re.search(r"<a?:[a-zA-Z0-9_]+:\d+>", content) or any(emoji.is_emoji(char) for char in content):
                await message.channel.send(f"{message.author.mention}, sua mensagem contém emotes ou emojis, que não são permitidos. Envie apenas texto puro.")
                return
            if re.search(r"https?://|www\.", content, re.IGNORECASE):
                await message.channel.send(f"{message.author.mention}, sua mensagem contém links, que não são permitidos. Envie apenas texto puro.")
                return
            if message.attachments:
                await message.channel.send(f"{message.author.mention}, sua mensagem contém anexos, que não são permitidos. Envie apenas texto puro.")
                return
            if len(content) < 3:
                await message.channel.send(f"{message.author.mention}, sua mensagem é muito curta. Envie pelo menos 3 caracteres.")
                return

            if message.reference and message.reference.message_id in mensagens_perguntas[message.author.id]:
                topico = mensagens_perguntas[message.author.id][message.reference.message_id]
                if topico in respostas_por_usuario[message.author.id] and respostas_por_usuario[message.author.id][topico]:
                    await message.channel.send(f"{message.author.mention}, você já respondeu a este tópico. Não é possível alterar após o envio ao canal.")
                    return

                respostas_por_usuario[message.author.id][topico] = content
                print(f"✅ Resposta de '{message.author.display_name}' para '{topico}' registrada: {content}")

                if len(respostas_por_usuario[message.author.id]) == len(TOPICOS_PERGUNTAS):
                    guild_id = servidor_alvo.get(message.author.id)
                    canal_destino = None
                    if guild_id:
                        guild = bot.get_guild(guild_id)
                        if guild:
                            canal_destino = discord.utils.get(guild.text_channels, name=CANAL_DESTINO_NOME)

                    if canal_destino:
                        embed = discord.Embed(
                            title=f"🕊️ Edificação - {message.author.display_name}",
                            color=discord.Color.blue(),
                            description="✨ Edificação Concluída ✨"
                        )
                        for topico in TOPICOS_PERGUNTAS:
                            mensagem = respostas_por_usuario[message.author.id].get(topico, "Não respondido")
                            if topico == "Oração":
                                embed.add_field(name="🙏 **Oração:**", value=mensagem, inline=False)
                                embed.add_field(name="\u200B", value="\u200B", inline=False)
                            elif topico == "Dificuldade":
                                embed.add_field(name="💪 **Dificuldade:**", value=mensagem, inline=False)
                                embed.add_field(name="\u200B", value="\u200B", inline=False)
                            elif topico == "Comunhão":
                                embed.add_field(name="🤝 **Comunhão:**", value=mensagem, inline=False)
                                embed.add_field(name="\u200B", value="\u200B", inline=False)
                            elif topico == "Bíblico":
                                embed.add_field(name="📖 **Bíblico:**", value=mensagem, inline=False)
                        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
                        embed.set_footer(text="Sacerbot - Edificação Diária")
                        await canal_destino.send(embed=embed)
                        print(f"✅ Respostas de '{message.author.display_name}' enviadas para '{canal_destino.name}' (Servidor: {guild.name})")

                        del respostas_por_usuario[message.author.id]
                        del mensagens_perguntas[message.author.id]
                        del servidor_alvo[message.author.id]
                    else:
                        print(f"Canal '{CANAL_DESTINO_NOME}' não encontrado para o usuário {message.author.display_name}")
                        await message.channel.send(f"Erro: Canal '{CANAL_DESTINO_NOME}' não encontrado no servidor associado.")
            elif message.reference:
                await message.channel.send(f"{message.author.mention}, use a função 'Responder' para responder às perguntas enviadas por mim.")
            else:
                await message.channel.send(f"{message.author.mention}, use a função 'Responder' para responder às perguntas enviadas por mim.")
        except Exception as e:
            print(f"Erro ao processar mensagem de '{message.author.display_name}': {e}")
            await message.channel.send(f"Erro ao processar sua mensagem: {e}")

    await bot.process_commands(message)

@bot.command()
async def edificar(ctx):
    agora_utc = datetime.datetime.now(datetime.timezone.utc)
    agora = agora_utc - datetime.timedelta(hours=3)
    print(f"Comando !edificar chamado por {ctx.author.display_name} (ID: {ctx.author.id})")

    if ctx.guild:
        print(f"Servidor detectado: {ctx.guild.name} (ID: {ctx.guild.id})")
        cargo = discord.utils.get(ctx.guild.roles, name=CARGO_AUTORIZADO)
        if cargo:
            print(f"Cargo '{CARGO_AUTORIZADO}' encontrado no servidor {ctx.guild.name}")
            if CARGO_AUTORIZADO in [role.name for role in ctx.author.roles]:
                try:
                    print(f"Tentando enviar DM para {ctx.author.display_name} (ID: {ctx.author.id}) em {ctx.guild.name}")
                    for topico, pergunta in TOPICOS_PERGUNTAS.items():
                        mensagem = await ctx.author.send(pergunta)
                        mensagens_perguntas[ctx.author.id][mensagem.id] = topico
                        await asyncio.sleep(1)
                    servidor_alvo[ctx.author.id] = ctx.guild.id
                    await ctx.send(f"✅ Perguntas enviadas no privado para você (Servidor: {ctx.guild.name})")
                    print(f"Perguntas enviadas para {ctx.author.display_name}")
                except Exception as e:
                    print(f"Erro ao enviar perguntas para {ctx.author.display_name} em {ctx.guild.name}: {e}")
                    await ctx.send(f"Erro ao enviar perguntas: {e}")
                    owner = ctx.guild.owner
                    if owner:
                        await owner.send(f"Erro ao enviar perguntas no servidor '{ctx.guild.name}': {e}")
            else:
                print(f"Usuário {ctx.author.display_name} não tem o cargo '{CARGO_AUTORIZADO}'")
                await ctx.send(f"Você não tem o cargo '{CARGO_AUTORIZADO}' para usar este comando.")
        else:
            print(f"Cargo '{CARGO_AUTORIZADO}' não encontrado no servidor {ctx.guild.name}")
            await ctx.send(f"Cargo '{CARGO_AUTORIZADO}' não encontrado. Verifique o nome do cargo.")
            owner = ctx.guild.owner
            if owner:
                await owner.send(f"Cargo '{CARGO_AUTORIZADO}' não encontrado no servidor '{ctx.guild.name}'.")
    else:
        print("Comando usado em DMs")
        user = ctx.author
        guild_encontrado = None
        for guild in bot.guilds:
            member = guild.get_member(user.id)
            if member:
                cargo = discord.utils.get(guild.roles, name=CARGO_AUTORIZADO)
                if cargo and CARGO_AUTORIZADO in [role.name for role in member.roles]:
                    guild_encontrado = guild
                    break

        if guild_encontrado:
            print(f"Servidor encontrado para o usuário {user.display_name}: {guild_encontrado.name}")
            try:
                print(f"Tentando enviar DM para {user.display_name} (ID: {user.id}) em {guild_encontrado.name}")
                for topico, pergunta in TOPICOS_PERGUNTAS.items():
                    mensagem = await user.send(pergunta)
                    mensagens_perguntas[user.id][mensagem.id] = topico
                    await asyncio.sleep(1)
                servidor_alvo[user.id] = guild_encontrado.id
                await ctx.send(f"✅ Perguntas enviadas no privado para você (Servidor: {guild_encontrado.name})")
                print(f"Perguntas enviadas para {user.display_name}")
            except Exception as e:
                print(f"Erro ao enviar perguntas para {user.display_name}: {e}")
                await ctx.send(f"Erro ao enviar perguntas: {e}")
        else:
            print(f"Usuário {user.display_name} não tem o cargo '{CARGO_AUTORIZADO}' em nenhum servidor")
            await ctx.send(f"Você não tem o cargo '{CARGO_AUTORIZADO}' em nenhum servidor para usar este comando.")

@bot.command()
async def limpar(ctx):
    try:
        respostas_por_usuario.clear()
        mensagens_perguntas.clear()
        servidor_alvo.clear()
        await ctx.send("✅ Dicionário de respostas, perguntas e servidores alvo foi limpo!")
    except Exception as e:
        await ctx.send(f"Erro ao limpar dicionário: {e}")
        owner = ctx.guild.owner if ctx.guild else None
        if owner:
            await owner.send(f"Erro ao limpar dicionário: {e}")

@bot.command()
async def ajuda(ctx):
    embed = discord.Embed(
        title="🕊️ Comandos do Sacerbot",
        color=discord.Color.blue(),
        description="Aqui estão todos os comandos disponíveis!"
    )
    embed.add_field(name="!edificar", value="Inicia a edificação, enviando perguntas no privado para usuários com o cargo `sacerbot`.", inline=False)
    embed.add_field(name="!limpar", value="Limpa os dicionários de respostas, perguntas e servidores alvo (usado para testes).", inline=False)
    embed.add_field(name="!ajuda", value="Mostra esta lista de comandos disponíveis.", inline=False)
    embed.set_footer(text="Sacerbot - Edificação Diária")
    await ctx.send(embed=embed)

# Inicia o bot
bot.run(TOKEN)
