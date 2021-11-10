import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from config import config
from Bot import *

class Coininfo(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command(usage="coininfo <coin>", aliases=['coinf_info', 'coin'], description="Get coin's information in TipBot.")
    async def coininfo(self, ctx, coin: str = None):
        if coin is None:
            if isinstance(ctx.channel, discord.DMChannel) == False and ctx.guild.id == TRTL_DISCORD:
                return
            table_data = [
                ["TICKER", "Height", "Tip", "Wdraw", "Depth"]
                ]
            for COIN_NAME in [coinItem.upper() for coinItem in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH]:
                height = None
                if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                    token_info = await store.get_token_info(COIN_NAME)
                    confim_depth = token_info['deposit_confirm_depth']
                else:
                    confim_depth = get_confirm_depth(COIN_NAME)
                try:
                    openRedis()
                    if redis_conn and redis_conn.exists(f'{config.redis_setting.prefix_daemon_height}{COIN_NAME}'):
                        height = int(redis_conn.get(f'{config.redis_setting.prefix_daemon_height}{COIN_NAME}'))
                        if not is_maintenance_coin(COIN_NAME):
                            table_data.append([COIN_NAME,  '{:,.0f}'.format(height), "ON" if is_coin_tipable(COIN_NAME) else "OFF"\
                            , "ON" if is_coin_txable(COIN_NAME) else "OFF"\
                            , confim_depth])
                        else:
                            table_data.append([COIN_NAME, "***", "***", "***", confim_depth])
                except Exception as e:
                    await logchanbot(traceback.format_exc())

            table = AsciiTable(table_data)
            table.padding_left = 0
            table.padding_right = 0
            msg = await ctx.send('**[ TIPBOT COIN LIST ]**\n'
                                 f'```{table.table}```')
            
            return
        else:
            COIN_NAME = coin.upper()
            if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                token_info = await store.get_token_info(COIN_NAME)
                confim_depth = token_info['deposit_confirm_depth']
                Min_Tip = token_info['real_min_tip']
                Max_Tip = token_info['real_max_tip']
                Min_Tx = token_info['real_min_tx']
                Max_Tx = token_info['real_max_tx']
            elif COIN_NAME in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_XCH:
                confim_depth = get_confirm_depth(COIN_NAME)
                Min_Tip = get_min_mv_amount(COIN_NAME)
                Max_Tip = get_max_mv_amount(COIN_NAME)
                Min_Tx = get_min_tx_amount(COIN_NAME)
                Max_Tx = get_max_tx_amount(COIN_NAME)
                token_info = None
            if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
                await ctx.author.send(f'{ctx.author.mention} **{COIN_NAME}** is not in our list.')
                return
            else:
                response_text = "**[ COIN INFO {} ]**".format(COIN_NAME)
                response_text += "```"
                try:
                    openRedis()
                    if redis_conn and redis_conn.exists(f'{config.redis_setting.prefix_daemon_height}{COIN_NAME}'):
                        height = int(redis_conn.get(f'{config.redis_setting.prefix_daemon_height}{COIN_NAME}'))
                        response_text += "Height: {:,.0f}".format(height) + "\n"
                    response_text += "Confirmation: {} Blocks".format(confim_depth) + "\n"
                    tip_deposit_withdraw_stat = ["ON", "ON", "ON"]
                    if not is_coin_tipable(COIN_NAME):
                        tip_deposit_withdraw_stat[0] = "OFF"
                    if not is_coin_depositable(COIN_NAME):
                        tip_deposit_withdraw_stat[1] = "OFF"
                    if not is_coin_txable(COIN_NAME):
                        tip_deposit_withdraw_stat[2] = "OFF"
                    response_text += "Tipping / Depositing / Withdraw:\n   {} / {} / {}\n".format(tip_deposit_withdraw_stat[0], tip_deposit_withdraw_stat[1], tip_deposit_withdraw_stat[2])

                    get_tip_min_max = "Tip Min/Max:\n   " + num_format_coin(Min_Tip, COIN_NAME) + " / " + num_format_coin(Max_Tip, COIN_NAME) + " " + COIN_NAME
                    response_text += get_tip_min_max + "\n"
                    get_tx_min_max = "Withdraw Min/Max:\n   " + num_format_coin(Min_Tx, COIN_NAME) + " / " + num_format_coin(Max_Tx, COIN_NAME) + " " + COIN_NAME
                    response_text += get_tx_min_max + "\n"

                    if COIN_NAME in FEE_PER_BYTE_COIN + ENABLE_COIN_DOGE + ENABLE_XCH + ENABLE_XMR:
                        response_text += "Withdraw Tx Node Fee: {} {}\n".format(num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
                    elif COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                        if token_info['contract'] and len(token_info['contract']) == 42:
                            response_text += "Contract:\n   {}\n".format(token_info['contract'])
                        elif COIN_NAME in ENABLE_COIN_TRC and token_info['contract'] and len(token_info['contract']) > 4:
                            response_text += "Contract/Token ID:\n   {}\n".format(token_info['contract'])
                        response_text += "Withdraw Tx Fee: {} {}\n".format(num_format_coin(token_info['real_withdraw_fee'], COIN_NAME), COIN_NAME)
                        if token_info['real_deposit_fee'] and token_info['real_deposit_fee'] > 0:
                            response_text += "Deposit Tx Fee: {} {}\n".format(num_format_coin(token_info['real_deposit_fee'], COIN_NAME), COIN_NAME)
                    elif COIN_NAME in ENABLE_COIN_NANO:
                        # nothing
                        response_text += "Withdraw Tx Fee: Zero\n"
                    else:
                        response_text += "Withdraw Tx Fee: {} {}\n".format(num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)

                    if isinstance(ctx.channel, discord.DMChannel) == True:
                        if COIN_NAME in ENABLE_TRADE_COIN and is_tradeable_coin(COIN_NAME): 
                            response_text += f"Trade Min/Max: {num_format_coin(get_min_sell(COIN_NAME, token_info), COIN_NAME)} {COIN_NAME} / {num_format_coin(get_max_sell(COIN_NAME, token_info), COIN_NAME)} {COIN_NAME}\n"
                            
                    elif isinstance(ctx.channel, discord.DMChannel) == False and COIN_NAME in ENABLE_TRADE_COIN and is_tradeable_coin(COIN_NAME):
                        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
                        if 'enable_trade' in serverinfo and serverinfo['enable_trade'] == "YES":
                            response_text += f"Trade Min/Max: {num_format_coin(get_min_sell(COIN_NAME, token_info), COIN_NAME)} {COIN_NAME} / {num_format_coin(get_max_sell(COIN_NAME, token_info), COIN_NAME)} {COIN_NAME}\n"
                            # If there is volume
                            try:
                                get_trade = await store.sql_get_coin_trade_stat(COIN_NAME)
                                if get_trade:
                                    response_text += "Trade volume:\n   24h: {} {}\n".format(num_format_coin(get_trade['trade_24h'], COIN_NAME), COIN_NAME)
                                    response_text += "   7d: {} {}\n".format(num_format_coin(get_trade['trade_7d'], COIN_NAME), COIN_NAME)
                                    response_text += "   30d: {} {}\n".format(num_format_coin(get_trade['trade_30d'], COIN_NAME), COIN_NAME)
                            except Exception as e:
                                await logchanbot(traceback.format_exc())
                    if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC and token_info['coininfo_note']:
                        response_text += "\nNote:\n   {}\n".format(token_info['coininfo_note'])
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                response_text += "```"
                await ctx.message.reply(response_text)
                return


def setup(bot):
    bot.add_cog(Coininfo(bot))