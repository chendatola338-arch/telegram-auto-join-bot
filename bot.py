import os
import asyncio
import logging
import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ChatMemberHandler,
    filters,
    ContextTypes,
)
from aiohttp import web

from database import init_db, save_user, save_payment, get_payment, mark_payment_approved, has_user_paid
from payway import (
    create_payway_transaction,
    check_transaction_status,
    is_approved,
    generate_qr_code_image,
)

# Load Environment Variables
def get_config():
    load_dotenv(override=True)
    return {
        "BOT_TOKEN": os.getenv("BOT_TOKEN", "").strip(),
        "CHANNEL_ID": os.getenv("CHANNEL_ID", "").strip(),
        "ABA_PAYWAY_LINK": os.getenv("ABA_PAYWAY_LINK", "https://link.payway.com.kh/ABAPAYlP553382Z").strip(),
        "COURSE_TITLE": os.getenv("COURSE_TITLE", "វគ្គសិក្សាពិសេស (VIP Course)").strip(),
        "COURSE_DESCRIPTION": os.getenv("COURSE_DESCRIPTION", "ចូលរៀនវគ្គពិសេសជាមួយមេរៀនលម្អិត និងការ Support ផ្ទាល់").strip(),
        "COURSE_PRICE": float(os.getenv("COURSE_PRICE", "30.00")),
        "CURRENCY": os.getenv("CURRENCY", "USD").strip(),
        "ADMIN_ID": os.getenv("ADMIN_ID", "").strip(),
    }

config = get_config()
BOT_TOKEN = config["BOT_TOKEN"]
CHANNEL_ID = config["CHANNEL_ID"]
ABA_PAYWAY_LINK = config["ABA_PAYWAY_LINK"]
COURSE_TITLE = config["COURSE_TITLE"]
COURSE_DESCRIPTION = config["COURSE_DESCRIPTION"]
COURSE_PRICE = config["COURSE_PRICE"]
CURRENCY = config["CURRENCY"]
ADMIN_ID = config["ADMIN_ID"]

# Setup Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Track active polling tasks to avoid duplicates
active_polling_tasks = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler ពេល User ចុច /start
    """
    cfg = get_config()
    user = update.effective_user
    save_user(user.id, user.username or "", user.first_name or "", user.last_name or "")

    # ពិនិត្យមើលថាតើ User ធ្លាប់បានបង់ប្រាក់រួចហើយឬនៅ
    if has_user_paid(user.id):
        text = (
            f"👋 សួស្តី {user.first_name}!\n\n"
            f"✅ អ្នកបានចុះឈ្មោះ និងបង់ប្រាក់ក្នុង **{cfg['COURSE_TITLE']}** រួចរាល់ហើយ!\n\n"
            f"ប្រសិនបើអ្នកមិនទាន់បានចូល Channel ឬ Link ផុតកំណត់ សូមទាក់ទងមក Admin តាមរយៈ {cfg['ADMIN_ID'] if cfg['ADMIN_ID'] else 'ជំនួយការ'}។"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    welcome_text = (
        f"👋 សួស្តី **{user.first_name}** សូមស្វាគមន៍!\n\n"
        f"📚 **{cfg['COURSE_TITLE']}**\n"
        f"📝 {cfg['COURSE_DESCRIPTION']}\n\n"
        f"💰 **តម្លៃសិក្សា:** `${cfg['COURSE_PRICE']:.2f} {cfg['CURRENCY']}`\n\n"
        f"👇 សូមចុចប៊ូតុង **«បង់ប្រាក់ចូលរៀន»** ខាងក្រោម ដើម្បីទូទាត់ប្រាក់តាម ABA ឬ Bakong KHQR៖"
    )

    keyboard = [
        [InlineKeyboardButton("💳 បង់ប្រាក់ចូលរៀន (Pay to Join)", callback_data="pay_course")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_payment_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler ពេល User ចុចប៊ូតុងបង់ប្រាក់
    """
    cfg = get_config()
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    loading_msg = await query.message.reply_text("⏳ កំពុងបង្កើតវិក្កយបត្រ និង QR Code សូមរង់ចាំមួយភ្លែត...")

    tran_id = f"tx_{user.id}_{int(datetime.datetime.now().timestamp())}"

    try:
        # បង្កើត Transaction តាម JLA Payway API
        resp = await create_payway_transaction(
            amount=cfg["COURSE_PRICE"],
            aba_data_url=cfg["ABA_PAYWAY_LINK"],
            tran_id=tran_id
        )

        checkout_url = resp.get("checkout_url", "")
        deeplink = resp.get("deeplink", "")
        qr_string = resp.get("data", {}).get("qr_string", "")

        # បើគ្មាន qr_string ក្នុង data អាចយក checkout_url
        if not qr_string and resp.get("data"):
            qr_string = resp["data"].get("qr_string", checkout_url)

        # រក្សាទុកក្នុង Database
        save_payment(tran_id, user.id, cfg["COURSE_PRICE"], checkout_url, deeplink)

        # បង្កើតរូប QR Code មានស៊ុមស្អាត (KHQR Official Card)
        qr_image = generate_qr_code_image(
            qr_string if qr_string else checkout_url,
            amount=cfg["COURSE_PRICE"],
            currency=cfg["CURRENCY"]
        )

        caption = (
            f"🧾 **វិក្កយបត្របង់ប្រាក់ (KHQR Payment)**\n\n"
            f"📖 វគ្គសិក្សា: **{cfg['COURSE_TITLE']}**\n"
            f"💵 ចំនួនទឹកប្រាក់: `${cfg['COURSE_PRICE']:.2f} {cfg['CURRENCY']}`\n"
            f"🆔 លេខវិក្កយបត្រ: `{tran_id}`\n\n"
            f"📌 **របៀបបង់ប្រាក់:**\n"
            f"1️⃣ ស្កេន QR Code ខាងលើដោយប្រើ **ABA Mobile** ឬ App ធនាគារណាក៏បាន (Bakong KHQR)\n"
            f"2️⃣ ឬចុចប៊ូតុង **«📲 បើក ABA Mobile»** ខាងក្រោមដើម្បីបង់ភ្លាមៗ\n"
            f"3️⃣ បន្ទាប់ពីបង់រួច ប្រព័ន្ធនឹងផ្ញើ Link ចូលរៀនជូនស្វ័យប្រវត្តិ (Auto-Join Link) 🎉"
        )

        buttons = []
        # Telegram មិនអនុញ្ញាតអោយដាក់ url scheme abamobilebank:// លើ Inline Button ទេ ដូច្នេះត្រូវប្រើ checkout_url
        if checkout_url:
            buttons.append([InlineKeyboardButton("📲 បង់ប្រាក់តាម ABA Mobile / Web", url=checkout_url)])

        # ប៊ូតុងឆែកការបង់ប្រាក់ដោយដៃ + ប៊ូតុងបោះបង់
        buttons.append([
            InlineKeyboardButton("🔄 ខ្ញុំបានបង់រួចរាល់ (Check)", callback_data=f"check_{tran_id}")
        ])
        buttons.append([
            InlineKeyboardButton("❌ បោះបង់", callback_data=f"cancel_{tran_id}")
        ])

        reply_markup = InlineKeyboardMarkup(buttons)

        # លុប Loading message
        try:
            await loading_msg.delete()
        except Exception:
            pass

        # ផ្ញើរូបភាព QR Code ទៅ User
        sent_photo = await context.bot.send_photo(
            chat_id=user.id,
            photo=qr_image,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        # ចាប់ផ្តើម Background Task តាមដានការបង់ប្រាក់ (Auto-polling)
        task = asyncio.create_task(
            poll_payment_status(context, user.id, tran_id, sent_photo.message_id)
        )
        active_polling_tasks[tran_id] = task

    except Exception as e:
        logger.error(f"Error creating transaction: {e}", exc_info=True)
        try:
            await loading_msg.edit_text(
                f"❌ មានបញ្ហាក្នុងការបង្កើតការទូទាត់ សូមព្យាយាមម្តងទៀតនៅពេលក្រោយ。\n(Error: {str(e)})"
            )
        except Exception:
            await context.bot.send_message(
                chat_id=user.id,
                text=f"❌ មានបញ្ហាក្នុងការបង្កើតការទូទាត់ សូមព្យាយាមម្តងទៀតនៅពេលក្រោយ。\n(Error: {str(e)})"
            )

async def poll_payment_status(context: ContextTypes.DEFAULT_TYPE, user_id: int, tran_id: str, message_id: int):
    """
    Background Task: ពិនិត្យការបង់ប្រាក់រៀងរាល់ 4-5 វិនាទី រហូតដល់ 3 នាទី (180 វិនាទី)
    """
    max_duration = 180  # 3 នាទី
    interval = 5        # 5 វិនាទី
    start_time = asyncio.get_event_loop().time()

    logger.info(f"Started polling payment for tran_id: {tran_id}, user: {user_id}")

    while (asyncio.get_event_loop().time() - start_time) < max_duration:
        await asyncio.sleep(interval)
        try:
            status_data = await check_transaction_status(tran_id)
            if is_approved(status_data):
                logger.info(f"Payment approved for {tran_id}!")
                await deliver_channel_access(context, user_id, tran_id, message_id)
                break
        except Exception as e:
            logger.warning(f"Error during polling {tran_id}: {e}")

    active_polling_tasks.pop(tran_id, None)

async def deliver_channel_access(context: ContextTypes.DEFAULT_TYPE, user_id: int, tran_id: str, message_id: int = None):
    """
    បង្កើត One-Time Invite Link និងផ្ញើទៅកាន់ User
    """
    cfg = get_config()
    # ពិនិត្យមើលថាតើ Tran នេះត្រូវបាន Approve រួចហើយឬនៅដើម្បីកុំឱ្យផ្ញើ ២ ដង
    payment = get_payment(tran_id)
    if payment and payment.get("status") == "approved":
        return

    try:
        # បង្កើត Single-use Telegram Invite Link (ប្រើបានតែម្នាក់គត់)
        expire_date = datetime.datetime.now() + datetime.timedelta(hours=48)
        
        invite = await context.bot.create_chat_invite_link(
            chat_id=cfg["CHANNEL_ID"],
            member_limit=1,  # ប្រើបានតែម្តង ចូលហើយមិនអាច share ឱ្យអ្នកផ្សេងបានទេ
            name=f"Student_{user_id}_{tran_id[-6:]}",
            expire_date=expire_date
        )
        
        invite_link = invite.invite_link

        # Update Database
        mark_payment_approved(tran_id, invite_link)

        # ផ្ញើសារអបអរសាទរ និងប៊ូតុង Link ចូល Channel
        success_text = (
            f"🎉 **ការបង់ប្រាក់ទទួលបានជោគជ័យ!**\n\n"
            f"សូមស្វាគមន៍មកកាន់ **{cfg['COURSE_TITLE']}**!\n"
            f"ខាងក្រោមនេះជា Link ផ្ទាល់ខ្លួនរបស់អ្នកសម្រាប់ចូលរៀនក្នុង Channel (Link នេះប្រើបានតែម្តងគត់):\n\n"
            f"👉 [ចុចត្រង់នេះដើម្បីចូល Channel]({invite_link})\n\n"
            f"⚠️ *ចំណាំ: Link នេះសម្រាប់តែអ្នកប៉ុណ្ណោះ សូមកុំចែករំលែកទៅកាន់អ្នកដទៃ។*"
        )

        join_keyboard = [
            [InlineKeyboardButton("🚀 ចូលរៀនឥឡូវនេះ (Join Channel)", url=invite_link)]
        ]
        
        await context.bot.send_message(
            chat_id=user_id,
            text=success_text,
            reply_markup=InlineKeyboardMarkup(join_keyboard),
            parse_mode="Markdown"
        )

        # ផ្ញើដំណឹងប្រាប់ Admin (បើមានកំណត់ ADMIN_ID)
        if cfg["ADMIN_ID"]:
            try:
                admin_text = (
                    f"📢 **មានសិស្សថ្មីបានបង់ប្រាក់ចូលរៀន!**\n\n"
                    f"👤 User ID: `{user_id}`\n"
                    f"💵 ចំនួនទឹកប្រាក់: `${cfg['COURSE_PRICE']:.2f}`\n"
                    f"🆔 Tran ID: `{tran_id}`\n\n"
                    f"🔗 Invite Link: {invite_link}"
                )
                await context.bot.send_message(chat_id=cfg["ADMIN_ID"], text=admin_text, parse_mode="Markdown")
            except Exception as admin_err:
                logger.warning(f"Could not notify admin: {admin_err}")

    except Exception as e:
        logger.error(f"Error creating invite link: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ ការបង់ប្រាក់របស់អ្នកជោគជ័យ! ប៉ុន្តែមានបញ្ហាក្នុងការបង្កើត Link ដោយស្វ័យប្រវត្តិ។ សូមទាក់ទងមកកាន់ Admin ជាមួយវិក្កយបត្រ `{tran_id}`។"
        )

async def check_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler ពេល User ចុចប៊ូតុង "🔄 ខ្ញុំបានបង់រួចរាល់ (Check)"
    """
    query = update.callback_query
    tran_id = query.data.replace("check_", "")
    user = update.effective_user

    # ពិនិត្យស្ថានភាព
    status_data = await check_transaction_status(tran_id)
    if is_approved(status_data):
        await query.answer("🎉 ការទូទាត់ទទួលបានជោគជ័យ!", show_alert=True)
        await deliver_channel_access(context, user.id, tran_id, query.message.message_id)
    else:
        await query.answer("⏳ មិនទាន់ទទួលបានការទូទាត់នៅឡើយទេ។ ប្រសិនបើអ្នកទើបតែផ្ទេរ សូមរង់ចាំប្រហែល 5 ទៅ 10 វិនាទីរួចចុចម្តងទៀត។", show_alert=True)

async def cancel_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler ពេល User ចុច "❌ បោះបង់"
    """
    query = update.callback_query
    tran_id = query.data.replace("cancel_", "")
    
    # Cancel background polling task
    if tran_id in active_polling_tasks:
        active_polling_tasks[tran_id].cancel()
        active_polling_tasks.pop(tran_id, None)

    await query.answer("បានបោះបង់ការទូទាត់។")
    try:
        await query.message.delete()
    except Exception:
        pass

async def channel_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ស្វែងរក និងចាប់យក Channel ID ស្វ័យប្រវត្តិតាម channel_post
    """
    if update.channel_post and update.channel_post.chat:
        chat = update.channel_post.chat
        chat_id = str(chat.id)
        chat_title = chat.title
        logger.info(f"🎉 ស្គាល់ Channel: {chat_title} (ID: {chat_id})")
        
        # Save to .env if not yet set
        cfg = get_config()
        if cfg.get("CHANNEL_ID") != chat_id:
            logger.info(f"Saving CHANNEL_ID={chat_id} to .env")
            with open(".env", "r", encoding="utf-8") as f:
                content = f.read()
            import re
            new_content = re.sub(r"CHANNEL_ID=.*", f"CHANNEL_ID={chat_id}", content)
            with open(".env", "w", encoding="utf-8") as f:
                f.write(new_content)

            # Send a notification to Admin
            if cfg.get("ADMIN_ID"):
                await context.bot.send_message(
                    chat_id=cfg["ADMIN_ID"],
                    text=f"✅ **បានភ្ជាប់ Channel ជោគជ័យ!**\n\n📢 ឈ្មោះ: **{chat_title}**\n🆔 Channel ID: `{chat_id}`"
                )

async def start_health_server(app: Application):
    """
    HTTP Server សម្រាប់ Render.com Web Service Health Check
    """
    port_env = os.getenv("PORT")
    if not port_env:
        return
    port = int(port_env)
    async def handle_ping(request):
        return web.Response(text="Bot is running smoothly 24/7!")

    server = web.Application()
    server.router.add_get("/", handle_ping)
    server.router.add_get("/health", handle_ping)

    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Render health server listening on port {port}")

def main():
    """
    ដំណើរការ Telegram Bot
    """
    init_db()

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("="*60)
        print("❌ កំហុស: សូមបញ្ចូល BOT_TOKEN ក្នុង file .env ជាមុនសិន!")
        print("="*60)
        return

    if not CHANNEL_ID or CHANNEL_ID == "-1001234567890":
        print("="*60)
        print("⚠️ ការរំលឹក: សូមប្រាកដថាអ្នកបានកំណត់ CHANNEL_ID ក្នុង file .env ត្រឹមត្រូវ!")
        print("="*60)

    print("="*60)
    print("🚀 កំពុងដំណើរការ Bot Telegram Auto-Join...")
    print(f"📌 Course: {COURSE_TITLE} (${COURSE_PRICE})")
    print(f"📌 Payway Link: {ABA_PAYWAY_LINK}")
    print("="*60)

    app = Application.builder().token(BOT_TOKEN).post_init(start_health_server).build()

    # Commands & Callbacks
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(handle_payment_request, pattern="^pay_course$"))
    app.add_handler(CallbackQueryHandler(check_button_callback, pattern="^check_"))
    app.add_handler(CallbackQueryHandler(cancel_button_callback, pattern="^cancel_"))
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL, channel_post_handler))

    # Start Polling
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
