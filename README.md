# Telegram Bot Auto-Join Channel (ប្រព័ន្ធបង់ប្រាក់ស្វ័យប្រវត្តិតាម ABA PayWay / KHQR)

ប្រព័ន្ធនេះត្រូវបានបង្កើតឡើងសម្រាប់៖
1. **User ចុច `/start`** លើ Telegram Bot ដើម្បីមើលព័ត៌មានវគ្គសិក្សា
2. **User ចុចបង់ប្រាក់** -> Bot ហៅ JLA Payway API បង្កើតវិក្កយបត្រ Dynamic KHQR និងប៊ូតុង Deeplink ចូល ABA Mobile ភ្លាមៗ
3. **User ស្កេន ឬបង់ប្រាក់រួចរាល់** -> Bot ឆែកឃើញ `approved` ស្វ័យប្រវត្តិ
4. **Bot បង្កើត One-Time Invite Link** (Link ប្រើបានតែម្តងគត់ ចូលហើយចែករំលែកឱ្យអ្នកផ្សេងមិនកើត) និងផ្ញើឱ្យសិស្សចូលរៀនក្នុង Channel ភ្លាមៗ 100% ស្វ័យប្រវត្តិ។

---

## 🛠️ ឯកសារក្នុងគម្រោង

- `bot.py` : កូដមេរបស់ Telegram Bot (គ្រប់គ្រងប៊ូតុង, ការបង់ប្រាក់, Auto-polling, និងបង្កើត Link)
- `payway.py` : ផ្នែកទាក់ទងជាមួយ JLA Payway API (`create-tran`, `check-payment-status`) និងបង្កើតរូប QR Code
- `database.py` : ប្រព័ន្ធ SQLite Database សម្រាប់កត់ត្រាសិស្ស និងប្រតិបត្តិការបង់ប្រាក់
- `.env` : កន្លែងកំណត់ Token, Channel ID, តម្លៃវគ្គសិក្សា, និង ABA Payway Link
- `test_config.py` : Script សម្រាប់តេស្តមើលថា Bot Token និង Channel ID ដំណើរការត្រឹមត្រូវឬនៅ
- `start.bat` : គ្រាន់តែចុច Double Click ដើម្បីបើកដំណើរការ Bot លើ Windows

---

## 🚀 របៀបដំឡើង និងចាប់ផ្តើមដំណើរការ (Setup Guide)

### ជំហានទី ១: បង្កើត Telegram Bot និងយក Bot Token
1. បើកកម្មវិធី Telegram ហើយស្វែងរក **@BotFather**
2. វាយពាក្យបញ្ជា `/newbot`
3. ដាក់ឈ្មោះ Bot និង Username (ឧទាហរណ៍ `MyCoursePayBot`)
4. អ្នកនឹងទទួលបាន **HTTP API Token** (ឧទាហរណ៍ `7123456789:ABCdef...`)
5. ចម្លង Token នោះមកដាក់ក្នុង file `.env` ត្រង់បន្ទាត់ `BOT_TOKEN=`

---

### ជំហានទី ២: បញ្ចូល Bot ទៅក្នុង Telegram Channel របស់អ្នក
1. ចូលទៅកាន់ **Telegram Channel** (ឬ Group) ដែលអ្នកចង់ឱ្យសិស្សចូលរៀន
2. ចុចមើលព័ត៌មាន Channel -> ជ្រើសរើស **Administrators** -> ចុច **Add Administrator**
3. ស្វែងរក Username របស់ Bot របស់អ្នក រួច Add វាចូល
4. **សំខាន់បំផុត:** ត្រូវបើកសិទ្ធិ **«Invite Users via Link»** (ឬ «Add Subscribers») ឱ្យ Bot ដើម្បីឱ្យវាអាចបង្កើត Invite Link ជូនសិស្សបាន។

---

### ជំហានទី ៣: ស្វែងរក Channel ID
1. ផ្ញើសារមួយម៉ាត់ (ឧទាហរណ៍ "test") នៅក្នុង Channel នោះ
2. បើក Terminal ឬ Command Prompt ក្នុង Folder នេះ រួចវាយ៖
   ```bash
   python test_config.py
   ```
3. Script នឹងបង្ហាញលេខសម្គាល់ Channel ID របស់អ្នក (មានទម្រង់ជាសញ្ញាដក ឧទាហរណ៍: `-1002345678901`)
4. ចម្លងលេខ Channel ID នោះមកដាក់ក្នុង file `.env` ត្រង់បន្ទាត់ `CHANNEL_ID=`

---

### ជំហានទី ៤: កំណត់តម្លៃ និងព័ត៌មានក្នុង `.env`
បើក file `.env` អ្នកអាចកែសម្រួលបានតាមចិត្ត៖
```env
BOT_TOKEN=7123456789:ABCdef...
CHANNEL_ID=-1002345678901
ABA_PAYWAY_LINK=https://link.payway.com.kh/ABAPAYlP553382Z

COURSE_TITLE=វគ្គសិក្សាពិសេស (VIP Course)
COURSE_DESCRIPTION=ចូលរៀនវគ្គពិសេសជាមួយមេរៀនលម្អិត និងការ Support ផ្ទាល់
COURSE_PRICE=10.00
CURRENCY=USD

ADMIN_ID=123456789
```

---

### ជំហានទី ៥: ដំណើរការ Bot
- ចុច Double Click លើ file `start.bat`
- ឬវាយពាក្យបញ្ជាក្នុង Terminal:
  ```bash
  python bot.py
  ```

ឥឡូវនេះ Bot របស់អ្នកបានដំណើរការរួចរាល់ហើយ! អ្នកអាចចូលទៅក្នុង Telegram Bot របស់អ្នក ហើយចុច `/start` ដើម្បីសាកល្បងបង់ប្រាក់បាន។
