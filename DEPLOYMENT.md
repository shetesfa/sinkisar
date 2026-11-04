# 🚀 Synksar Auto Publisher - 24/7 ማሰማሪያ መመሪያ (Deployment Guide)

ይህ መመሪያ **Synksar Auto Publisher** ስርዓት ኮምፒዩተርዎ ቢጠፋም ወይም እርስዎ በሌሉበት ዓመቱን ሙሉ ያለማቋረጥ 24/7 በራሱ እንዲሰራ ለማድረግ የሚያስችሉ ቀላል አማራጮችን ያብራራል።

---

## 📌 ማጠቃለያ፦ ኮምፒዩተር ቢጠፋ ወይም ኢንተርኔት ቢቋረጥ ምን ይሆናል?

- **Offline Catch-Up / Startup Recovery**፦
  የስርዓቱ መርሐግብር (Scheduler) ኮምፒዩተሩ ሲበራ ወይም አፕሊኬሽኑ ዳግም ሲነሳ **የዛሬው ቀን ስንክሳር መታተሙን በቅድሚያ ያረጋግጣል**።
  ለምሳሌ፡ ኮምፒዩተርዎ እኩለ ሌሊት 12:00 AM ላይ ጠፍቶ ከነበረና ጠዋት 2:00 ላይ ቢበራ፣ አፕሊኬሽኑ እንደተነሳ ወዲያውኑ የዛሬው ቀን አለመታተሙን ተመልክቶ በሰከንዶች ውስጥ ወደ ቻናሉ ያትመዋል!
- **ድጋሚ ህትመት ጥበቃ**፦
  ኮምፒዩተሩ በቀን ውስጥ በተደጋጋሚ ቢጠፋና ቢበራ እንኳን፣ አንድ ቀን አንዴ ከታተመ በኋላ በድጋሚ በፍጹም አይለጠፍም።

---

## አማራጭ ፩፦ በግል ኮምፒዩተር ላይ በራስ-ሰር እንዲነሳ ማድረግ (Windows Startup / Task Scheduler)

ኮምፒዩተርዎ በበራ ቁጥር ሲስተሙ በጀርባ (Background) በራሱ እንዲነሳ ለማድረግ፦

### ዘዴ A. በ Windows Startup Folder (በጣም ቀላሉ መንገድ)

1. በኪቦርድዎ ላይ `Windows + R` ን ይጫኑ።
2. በሚመጣው ሳጥን ውስጥ `shell:startup` ብለው ጽፈው Enter ይበሉ።
3. በሚከፈተው ፎልደር ውስጥ አዲስ Shortcut ወይም `start_synksar.bat` የሚል ፋይል ይፍጠሩ።
4. የ `start_synksar.bat` ፋይሉ ይዘት የሚከተለው ይሆናል፦
   ```bat
   @echo off
   cd /d "E:\ስንክሳር"
   start "" pythonw.exe main.py
   ```
   *(ማስታወሻ፦ `pythonw.exe` የጥቁር መስኮት (Terminal) ሳያሳይ በጀርባ በጸጥታ እንዲሰራ ያደርገዋል)*።

### ዘዴ B. በ Windows Task Scheduler (ተግባር መርሐግብር)

1. በዊንዶውስ ሰርች ባር ላይ **Task Scheduler** ብለው ይፈልጉና ይክፈቱት።
2. በቀኝ በኩል **Create Basic Task** የሚለውን ይጫኑ።
3. ስም፦ `Synksar Auto Publisher` ብለው ይሰጡት።
4. Trigger፦ **When the computer starts** (ኮምፒዩተሩ ሲበራ) የሚለውን ይምረጡ።
5. Action፦ **Start a program** የሚለውን ይምረጡ።
6. Program/script፦ የ Python መገኛዎን ያስገቡ (ለምሳሌ `python.exe`)።
7. Add arguments፦ `main.py`
8. Start in፦ `E:\ስንክሳር`
9. **Finish** የሚለውን ይጫኑ። አሁን ኮምፒዩተርዎ በበራ ቁጥር ስርዓቱ በራሱ ይሰራል!

---

## አማራጭ ፪፦ በነጻ ወይም በርካሽ ክላውድ ሰርቨር 24/7 ማስኬድ (Cloud Hosting - ኮምፒዩተር ሳይበራ)

ኮምፒዩተርዎ ሁልጊዜ ክፍት እንዳይሆን ከፈለጉ፣ ፕሮጀክቱን ወደ ክላውድ በመስቀል 24/7 ማስኬድ ይችላሉ።

### 1. በ Docker (ዶከር) ማስኬድ

በማውጫው ውስጥ የሚገኘውን `Dockerfile` በመጠቀም፦
```bash
# Docker Image መገንባት
docker build -t synksar-publisher .

# Docker Container ማስኬድ
docker run -d --name synksar --restart always -p 5000:5000 -v $(pwd)/synksar.db:/app/synksar.db synksar-publisher
```

### 2. በ Render.com ወይም Koyeb (ነጻ ክላውድ)
1. ፕሮጀክትዎን ወደ የግል GitHub Repository ይስቀሉት (Push ያድርጉት)።
2. በ [Render.com](https://render.com) ወይም [Koyeb.com](https://koyeb.com) ላይ አካውንት ይክፈቱ።
3. **New Web Service** የሚለውን መርጠው የ GitHub Repositoryዎን ያገናኙ።
4. Environment Variables ላይ የሚከተሉትን ይሙሉ፦
   - `BOT_TOKEN`
   - `CHANNEL_ID`
   - `ADMIN_IDS`
   - `TIMEZONE=Africa/Addis_Ababa`
   - `PUBLISH_HOUR=0`
   - `PUBLISH_MINUTE=0`
5. Start Command፦ `python main.py`
6. Deploy የሚለውን ይጫኑ። በደቂቃዎች ውስጥ ዓመቱን ሙሉ 24/7 በነጻ መስራት ይጀምራል!

### 3. በርካሽ ሊኑክስ ቪፒኤስ (VPS - ለምሳሌ Hetzner, DigitalOcean $4/month)
1. በቪፒኤስዎ ውስጥ ኮዱን ይክፈቱ።
2. `systemd` ሰርቪስ ይፍጠሩ፦
   `/etc/systemd/system/synksar.service`
   ```ini
   [Unit]
   Description=Synksar Auto Publisher
   After=network.target

   [Service]
   User=root
   WorkingDirectory=/root/synksar
   ExecStart=/usr/bin/python3 main.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```
3. ያስጀምሩት፦
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable synksar
   sudo systemctl start synksar
   ```

---

## 📞 ድጋፍ እና ማስተካከያ
ማንኛውም ችግር ወይም ጥያቄ ሲያጋጥም በዌብ ዳሽቦርዱ (http://localhost:5000) ላይ የ `History` እና `Validation Report` ገጾችን ይመልከቱ።
