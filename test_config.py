import os
import asyncio
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()

async def test_setup():
    print("=" * 60)
    print("🔍 កំពុងពិនិត្យការកំណត់ (Checking Bot Configuration)...")
    print("=" * 60)

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("❌ [ខ្វះខាត] មិនទាន់មាន BOT_TOKEN ក្នុង file .env នៅឡើយទេ!")
        print("👉 របៀបយក: ចូល Telegram ស្វែងរក @BotFather រួចវាយ /newbot ដើម្បីយក Token")
        return

    bot = Bot(token=BOT_TOKEN)

    # 1. ពិនិត្យ Bot Token
    try:
        me = await bot.get_me()
        print(f"✅ Bot Token ត្រឹមត្រូវ! ឈ្មោះ Bot: @{me.username} ({me.first_name})")
    except Exception as e:
        print(f"❌ Bot Token មិនត្រឹមត្រូវ: {e}")
        return

    # 2. ពិនិត្យ Channel ID
    if not CHANNEL_ID or CHANNEL_ID == "-1001234567890":
        print("\n⚠️ [ខ្វះខាត] មិនទាន់មាន CHANNEL_ID ត្រឹមត្រូវក្នុង file .env នៅឡើយទេ!")
        print("💡 របៀបស្វែងរក Channel ID:")
        print("   1. Add Bot (@" + me.username + ") ចូលក្នុង Telegram Channel របស់អ្នកជា Admin")
        print("   2. បើកសិទ្ធិ 'Invite Users via Link'")
        print("   3. ផ្ញើសារមួយម៉ាត់ក្នុង Channel នោះ")
        print("   4. ដំណើរការ script នេះម្តងទៀត ប្រព័ន្ធនឹងស្វែងរក ID ជូនអ្នកស្វ័យប្រវត្តិ។")

        # ស្វែងរកពី Updates
        updates = await bot.get_updates()
        found_channels = set()
        for u in updates:
            if u.channel_post and u.channel_post.chat:
                found_channels.add((u.channel_post.chat.id, u.channel_post.chat.title))
        
        if found_channels:
            print("\n🎉 រកឃើញ Channel របស់អ្នក:")
            for cid, title in found_channels:
                print(f"   👉 ឈ្មោះ: {title} | ID: {cid}")
                print(f"   (សូមចម្លង ID `{cid}` នេះទៅដាក់ក្នុង file .env)")
        return

    # 3. ពិនិត្យសិទ្ធិក្នុង Channel
    try:
        chat = await bot.get_chat(chat_id=CHANNEL_ID)
        print(f"✅ រកឃើញ Channel: {chat.title} (ID: {chat.id})")
        
        # សាកល្បងបង្កើត Link មួយដើម្បីតេស្តសិទ្ធិ
        test_link = await bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1, name="Test_Link")
        print(f"✅ សិទ្ធិ Admin ត្រឹមត្រូវ 100%! អាចបង្កើត Invite Link បានជោគជ័យ:")
        print(f"   👉 Link: {test_link.invite_link}")
        # លុប link តេស្ត
        await bot.revoke_chat_invite_link(chat_id=CHANNEL_ID, invite_link=test_link.invite_link)
        print("🎉 ប្រព័ន្ធរបស់អ្នករួចរាល់ 100% សម្រាប់ដំណើរការ!")
    except Exception as e:
        print(f"❌ មិនអាចចូល ឬបង្កើត Invite Link ក្នុង Channel បានទេ: {e}")
        print("⚠️ សូមប្រាកដថា:")
        print("   1. បាន Add Bot ចូលក្នុង Channel")
        print("   2. បានដំឡើង Bot ទៅជា 'Administrator'")
        print("   3. បានបើកសិទ្ធិ 'Invite Users via Link' (ឬ 'Add Subscribers')")

if __name__ == "__main__":
    asyncio.run(test_setup())
