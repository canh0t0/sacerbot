import discord
from discord.ext import commands, tasks
import datetime
from collections import defaultdict
import asyncio
import re
import emoji
import os
import random

# Token do bot
TOKEN = os.getenv('DISCORD_TOKEN')
print(f"DEBUG: TOKEN carregado como: {TOKEN}")

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

# Lista para armazenar as frases
frases = []

# Carregar frases do arquivo frases_sacerbot.txt
try:
    with open('frases_sacerbot.txt', 'r', encoding='utf-8') as file:
        frases = [linha.strip() for linha in file if linha.strip() and not linha.startswith('[')]
    print(f"✅ {len(frases)} frases carregadas do arquivo frases_sacerbot.txt")
except FileNotFoundError:
    print("Erro: Arquivo frases_sacerbot.txt não encontrado.")
except Exception as e:
    print(f"Erro ao carregar frases: {e}")

respostas_por_usuario = defaultdict(lambda: defaultdict(str))
mensagens_perguntas = defaultdict(dict)
servidor_alvo = {}

# Variável para rastrear a última frase postada
ultima_frase_data = None
frase_do_dia = None

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} está online!")
    lembrete_quinta.start()
    limpar_threads_quinta.start()
    postar_frase_diaria.start()  # Inicia a tarefa de postar frases diárias

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

@tasks.loop(minutes=1)
async def postar_frase_diaria():
    global ultima_frase_data, frase_do_dia
    agora_utc = datetime.datetime.now(datetime.timezone.utc)
    agora = agora_utc - datetime.timedelta(hours=3)  # UTC-3

    # Verifica se é 9h da manhã e se passou 48 horas desde a última postagem
    if agora.hour == 9 and agora.minute == 0:
        if ultima_frase_data is None or (agora.date() - ultima_frase_data).days >= 2:
            if frases:
                frase_do_dia = random.choice(frases)
                ultima_frase_data = agora.date()

                for guild in bot.guilds:
                    canal_destino = discord.utils.get(guild.text_channels, name=CANAL_DESTINO_NOME)
                    if canal_destino:
                        embed = discord.Embed(
                            title="📜 Frase Devocional",
                            color=discord.Color.gold(),
                            description=frase_do_dia
                        )
                        embed.set_footer(text="Sacerbot - Edificação Diária")
                        await canal_destino.send(embed=embed)
                        print(f"[{agora}] Frase postada no canal '{canal_destino.name}' (Servidor: {guild.name}): {frase_do_dia}")
                    else:
                        print(f"Canal '{CANAL_DESTINO_NOME}' não encontrado no servidor '{guild.name}'")

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
    embed.add_field(name="!frase", value="Envia uma frase devocional aleatória (disponível para usuários com o cargo `sacerbot`).", inline=False)
    embed.add_field(name="!exortar", value="Exorta um membro aleatório com o cargo 'sacerbot' no canal 'edificação' (disponível para usuários com o cargo `sacerbot`).", inline=False)
    embed.add_field(name="!limpar", value="Limpa os dicionários de respostas, perguntas e servidores alvo (usado para testes).", inline=False)
    embed.add_field(name="!ajuda", value="Mostra esta lista de comandos disponíveis.", inline=False)
    embed.set_footer(text="Sacerbot - Edificação Diária")
    await ctx.send(embed=embed)

@bot.command()
async def frase(ctx):
    # Verifica se o usuário tem o cargo "sacerbot" em algum servidor
    user = ctx.author
    guild_encontrado = None
    for guild in bot.guilds:
        member = guild.get_member(user.id)
        if member:
            cargo = discord.utils.get(guild.roles, name=CARGO_AUTORIZADO)
            if cargo and CARGO_AUTORIZADO in [role.name for role in member.roles]:
                guild_encontrado = guild
                break

    if not guild_encontrado:
        await ctx.send(f"Você não tem o cargo '{CARGO_AUTORIZADO}' em nenhum servidor para usar este comando.")
        return

    # Verifica se há frases carregadas
    if not frases:
        await ctx.send("Nenhuma frase disponível no momento.")
        return

    # Escolhe uma frase aleatória e envia
    frase_aleatoria = random.choice(frases)
    embed = discord.Embed(
        title="📜 Frase Devocional",
        color=discord.Color.gold(),
        description=frase_aleatoria
    )
    embed.set_footer(text="Sacerbot - Edificação Diária")
    await ctx.send(embed=embed)
    print(f"Frase enviada para {ctx.author.display_name} via comando !frase: {frase_aleatoria}")

# Lista de exortações sacerdotais (ajustada para "Irmão(ã)" e menção)
EXORTACOES = [
    "Ó {mention}, teme ao Senhor e aparta-te do mal, pois 'o temor do Senhor é o princípio da sabedoria' (Provérbios 9:10)! Não sejas negligente na tua santificação!",
    "Irmão(ã) {mention}, não confies nas tuas obras vãs, pois 'pela graça sois salvos, mediante a fé' (Efésios 2:8). Arrepende-te e crê somente em Cristo!",
    "Irmão(ã) {mention}, por que te esqueces da Palavra? 'Examinai as Escrituras', ordenou o Mestre (João 5:39). Não sejas um ouvinte negligente, mas um cumpridor da verdade!",
    "Irmão(ã) {mention}, o pecado te cerca! Foge dele, pois 'o salário do pecado é a morte' (Romanos 6:23). Volta-te para Deus e vive na Sua justiça!",
    "Ó {mention}, não sejas morno na fé, pois o Senhor 'vomitará os mornos da Sua boca' (Apocalipse 3:16)! Sê fervoroso e ardente no Espírito!",
    "Peregrino {mention}, a soberania de Deus te chama à obediência! 'Obedecei a Deus e não aos homens' (Atos 5:29). Não resistas à vontade do Altíssimo!",
    "Ó {mention}, onde está teu temor a Deus? 'O Senhor corrige a quem ama' (Hebreus 12:6). Treme diante da Sua santidade e busca a retidão!",
    "Irmão(ã) {mention}, não te envergonhes do Evangelho, pois ele é 'o poder de Deus para salvação' (Romanos 1:16)! Proclama a verdade com ousadia!",
    "Irmão(ã) {mention}, por que te desvias do caminho? 'Estreita é a porta que conduz à vida' (Mateus 7:14). Retorna ao Senhor com todo teu coração!",
    "Ó {mention}, não te glories na tua força, pois 'o coração do homem é enganoso' (Jeremias 17:9). Humilha-te diante de Deus e Ele te exaltará!",
    "Irmão(ã) {mention}, a oração é teu dever! 'Orai sem cessar' (1 Tessalonicenses 5:17), pois sem comunhão com Deus, tua alma perecerá na secura!",
    "Ó {mention}, não ames o mundo, pois 'a amizade com o mundo é inimizade contra Deus' (Tiago 4:4). Escolhe hoje a quem servirás!",
    "Irmão(ã) {mention}, a fé sem obras é morta (Tiago 2:17)! Mostra tua fé pelas tuas ações, ou serás julgado como um servo inútil!",
    "Ó {mention}, por que te calas diante do pecado? 'Denunciai o erro', diz o Senhor (Isaías 58:1). Não sejas cúmplice da iniqüidade!",
    "Irmão(ã) {mention}, busca o Reino de Deus em primeiro lugar (Mateus 6:33), ou todas as tuas prioridades serão vaidade e tormento de espírito!",
    "Ó {mention}, não te deixes enganar pelos falsos mestres, pois 'muitos virão em Meu nome' (Mateus 24:5). Apega-te à sã doutrina!",
    "Irmão(ã) {mention}, o dia do Senhor se aproxima! 'Preparai-vos para encontrar o vosso Deus' (Amós 4:12). Não sejas achado em falta!",
    "Ó {mention}, não enduresças teu coração, pois 'hoje, se ouvirdes a Sua voz, não endureçais' (Hebreus 3:15). Ouve o chamado do Espírito!",
    "Irmão(ã) {mention}, a soberania divina te escolheu! 'Não fostes vós que me escolhestes, mas Eu vos escolhi' (João 15:16). Vive digno da tua vocação!",
    "Ó {mention}, por que te esqueces da cruz? 'Cristo morreu por nós, sendo nós ainda pecadores' (Romanos 5:8). Vive em gratidão ao Redentor!",
    "Irmão(ã) {mention}, não te glories na tua justiça, pois 'todos pecaram e carecem da glória de Deus' (Romanos 3:23). Clama pela misericórdia divina!",
    "Ó {mention}, a Palavra é tua espada! 'Toma a espada do Espírito' (Efésios 6:17) e combate o bom combate da fé com ousadia!",
    "Irmão(ã) {mention}, não te conformes com este século (Romanos 12:2)! Sê transformado e separado para a glória de Deus!",
    "Ó {mention}, o Espírito te convence do pecado (João 16:8). Não resistas à voz de Deus, mas arrepende-te e busca a santificação!",
    "Irmão(ã) {mention}, por que negligencias a comunhão? 'Não deixemos de congregar-nos' (Hebreus 10:25). Fortalece-te com os irmãos na fé!",
    "Ó {mention}, a graça de Deus te basta (2 Coríntios 12:9)! Não murmures nas provações, mas confia na força do Altíssimo!",
    "Irmão(ã) {mention}, o temor a Deus te falta! 'Temei a Deus e dai-Lhe glória' (Apocalipse 14:7). Não sejas negligente diante do Santo!",
    "Ó {mention}, não te vanglories na tua sabedoria, pois 'a sabedoria deste mundo é loucura diante de Deus' (1 Coríntios 3:19). Busca a sabedoria celestial!",
    "Irmão(ã) {mention}, a santidade é teu chamado! 'Sede santos, porque Eu sou santo' (1 Pedro 1:16). Não te manches com as obras das trevas!",
    "Ó {mention}, por que te esqueces do dia do juízo? 'Presta contas ao teu Criador' (Eclesiastes 12:1). Prepara-te para o tribunal de Cristo!",
    "Irmão(ã) {mention}, a fé é tua âncora! 'Sem fé é impossível agradar a Deus' (Hebreus 11:6). Crê e não duvides da promessa divina!",
    "Ó {mention}, não te envolvas com jugo desigual (2 Coríntios 6:14)! Sê separado e consagrado ao serviço do Senhor!",
    "Irmão(ã) {mention}, o amor ao dinheiro te destrói, pois 'a raiz de todos os males é o amor ao dinheiro' (1 Timóteo 6:10). Busca as riquezas do Reino!",
    "Ó {mention}, não te cales diante da injustiça! 'Fazei justiça ao órfão e à viúva' (Isaías 1:17). Sê voz dos oprimidos em nome do Senhor!",
    "Irmão(ã) {mention}, a cruz é tua glória! 'Longe de mim gloriar-me, senão na cruz de Cristo' (Gálatas 6:14). Não te envergonhes do sacrifício!",
    "Ó {mention}, a paciência te é exigida! 'Alegrai-vos na esperança, sede pacientes na tribulação' (Romanos 12:12). Suporta com fé!",
    "Irmão(ã) {mention}, por que te desvias da verdade? 'A Tua palavra é a verdade' (João 17:17). Retorna à Escritura e firma-te na rocha!",
    "Ó {mention}, não te glories na tua força, pois 'o poder pertence a Deus' (Salmos 62:11). Depende d’Ele em toda a tua jornada!",
    "Irmão(ã) {mention}, o arrependimento é teu chamado! 'Arrependei-vos, pois o Reino de Deus está próximo' (Mateus 4:17). Não tardes em voltar-te para Deus!",
    "Ó {mention}, a humildade te falta! 'Quem se exalta será humilhado' (Mateus 23:12). Humilha-te perante o Senhor e Ele te erguerá!",
    "Irmão(ã) {mention}, não te esqueças do pobre, pois 'quem dá ao pobre empresta a Deus' (Provérbios 19:17). Sê generoso como Cristo foi!",
    "Ó {mention}, a perseverança é tua prova! 'Aquele que perseverar até o fim será salvo' (Mateus 24:13). Não desistas do caminho estreito!",
    "Irmão(ã) {mention}, a soberania de Deus te guia! 'Os passos do homem são dirigidos pelo Senhor' (Provérbios 20:24). Submete-te à Sua vontade!",
    "Ó {mention}, não te cales na adoração! 'Louvai ao Senhor, porque Ele é bom' (Salmos 136:1). Exalta o nome do Altíssimo em todo tempo!",
    "Irmão(ã) {mention}, a ira te consome! 'A ira do homem não opera a justiça de Deus' (Tiago 1:20). Busca a paz que vem do Espírito!",
    "Ó {mention}, por que te esqueces da eternidade? 'Que aproveita ao homem ganhar o mundo e perder a sua alma?' (Marcos 8:36). Busca o que é eterno!",
    "Irmão(ã) {mention}, a gratidão te falta! 'Em tudo dai graças' (1 Tessalonicenses 5:18). Reconhece as bênçãos do Senhor em tua vida!",
    "Ó {mention}, o Espírito te chama à santificação! 'Fugi da imoralidade' (1 Coríntios 6:18). Sê puro para o serviço do Reino!",
    "Irmão(ã) {mention}, não te deixes levar pela vanglória! 'Nada façais por vanglória, mas por humildade' (Filipenses 2:3). Sê servo em tudo!",
    "Ó {mention}, a Palavra é teu sustento! 'Nem só de pão viverá o homem, mas de toda palavra de Deus' (Mateus 4:4). Alimenta tua alma com a verdade!",
    "Irmão(ã) {mention}, a soberania divina te corrige! 'O Senhor disciplina a quem ama' (Provérbios 3:12). Aceita a correção e cresce na fé!",
    "Ó {mention}, não te esqueças do amor! 'Amai-vos uns aos outros, como Eu vos amei' (João 13:34). Sê reflexo do amor de Cristo!",
    "Irmão(ã) {mention}, o temor ao homem te prende! 'Em Deus confio, não temerei' (Salmos 56:4). Sê corajoso na obra do Senhor!",
    "Ó {mention}, por que negligencias a oração? 'Pedi, e dar-se-vos-á' (Mateus 7:7). Clama ao Senhor e Ele te ouvirá!",
    "Irmão(ã) {mention}, a fé te sustenta nas tormentas! 'Não temas, pois Eu sou contigo' (Isaías 41:10). Confia no Deus que acalma os ventos!",
    "Ó {mention}, não te deixes enganar pelo orgulho! 'O orgulho precede a ruína' (Provérbios 16:18). Humilha-te e busca a graça de Deus!",
    "Irmão(ã) {mention}, a verdade te liberta! 'Conhecereis a verdade, e a verdade vos libertará' (João 8:32). Apega-te à Palavra e sê livre!",
    "Ó {mention}, não te cales na proclamação! 'Ide e fazei discípulos' (Mateus 28:19). Sê testemunha fiel do Evangelho!",
    "Irmão(ã) {mention}, a paciência é tua virtude! 'Esperai no Senhor e sede fortes' (Salmos 27:14). Não te apresses, mas confia no tempo de Deus!",
    "Ó {mention}, o pecado te escraviza! 'Quem comete pecado é escravo do pecado' (João 8:34). Clama pela libertação do Senhor!",
    "Irmão(ã) {mention}, a comunhão é tua força! 'Onde dois ou três estão reunidos em Meu nome, ali estou' (Mateus 18:20). Não te afastes dos irmãos!",
    "Ó {mention}, por que te esqueces da cruz? 'Cristo padeceu por vós' (1 Pedro 2:21). Vive em memória do sacrifício do Cordeiro!",
    "Irmão(ã) {mention}, a santidade é tua meta! 'Sem santidade ninguém verá o Senhor' (Hebreus 12:14). Purifica-te para a glória de Deus!",
    "Ó {mention}, não te deixes abater! 'Não temas, pois Eu te remi' (Isaías 43:1). O Senhor é teu refúgio e fortaleza!",
    "Irmão(ã) {mention}, a humildade te exalta! 'Quem se humilhar será exaltado' (Lucas 14:11). Sê humilde e o Senhor te honrará!",
    "Ó {mention}, a Palavra te guia! 'Lâmpada para os meus pés é a Tua palavra' (Salmos 119:105). Não te desvies do caminho da luz!",
    "Irmão(ã) {mention}, o amor é teu mandamento! 'Amarás o teu próximo como a ti mesmo' (Mateus 22:39). Sê luz na vida do teu irmão!",
    "Ó {mention}, a perseverança te coroa! 'Sê fiel até a morte, e dar-te-ei a coroa da vida' (Apocalipse 2:10). Não retrocedas na jornada!",
    "Irmão(ã) {mention}, o Espírito te renova! 'Renovai-vos no espírito do vosso entendimento' (Efésios 4:23). Busca a transformação divina!"
]

@bot.command()
async def exortar(ctx):
    # Verifica se o usuário tem o cargo "sacerbot" (no servidor ou em algum servidor se for DM)
    user = ctx.author
    guild_encontrado = ctx.guild if ctx.guild else None
    if not guild_encontrado:
        for guild in bot.guilds:
            member = guild.get_member(user.id)
            if member and CARGO_AUTORIZADO in [role.name for role in member.roles]:
                guild_encontrado = guild
                break
    else:
        if CARGO_AUTORIZADO not in [role.name for role in user.roles]:
            await ctx.send(f"Você não tem o cargo '{CARGO_AUTORIZADO}' para usar este comando.")
            return

    if not guild_encontrado:
        await ctx.send(f"Você não tem o cargo '{CARGO_AUTORIZADO}' em nenhum servidor para usar este comando.")
        return

    # Encontra o canal "edificação" no servidor
    canal_edificacao = discord.utils.get(guild_encontrado.text_channels, name=CANAL_DESTINO_NOME)
    if not canal_edificacao:
        await ctx.send(f"Erro: Canal '{CANAL_DESTINO_NOME}' não encontrado no servidor.")
        return

    # Seleciona um membro aleatório com o cargo "sacerbot" (excluindo o bot)
    membros_com_cargo = [member for member in guild_encontrado.members if not member.bot and CARGO_AUTORIZADO in [role.name for role in member.roles]]
    if not membros_com_cargo:
        await ctx.send("Não há membros com o cargo 'sacerbot' para exortar neste servidor.")
        return

    alvo = random.choice(membros_com_cargo)
    exortacao = random.choice(EXORTACOES).format(mention=alvo.mention)

    # Envia a exortação no canal "edificação"
    embed = discord.Embed(
        title="🕊️ Exortação Sacerdotal",
        color=discord.Color.dark_purple(),
        description=exortacao
    )
    embed.set_footer(text="Sacerbot - Chamado à Santidade")
    await canal_edificacao.send(embed=embed)
    print(f"Exortação enviada para {alvo.display_name} por {ctx.author.display_name} no canal {canal_edificacao.name}")
    if __name__ == "__main__":
        bot.run(TOKEN)

