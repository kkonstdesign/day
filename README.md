# YouTube Downloader

Небольшое веб-приложение: вставляете ссылку на видео с YouTube — файл скачивается на компьютер.

Использует [yt-dlp](https://github.com/yt-dlp/yt-dlp) для получения видео. Для личного использования — скачивайте только то, на что у вас есть право (собственные видео, публичный домен, контент с разрешением автора).

## Установка

Нужен Python 3.10+ (системный Python 3.9 на macOS слишком старый для актуального yt-dlp). Если ещё не поставлен:

```bash
brew install python@3.12 ffmpeg
```

Дальше:

```bash
/usr/local/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`ffmpeg` нужен, чтобы скачивать видео и звук в максимальном качестве и склеивать их в один файл — без него приложение тоже работает, но берёт вариант похуже, где видео и звук уже объединены заранее.

## Запуск

```bash
source .venv/bin/activate
python3 app.py
```

Откройте [http://localhost:5001](http://localhost:5001), вставьте ссылку и нажмите «Скачать».

## PO Token провайдер (уже настроен)

YouTube в 2025–2026 ввёл дополнительную защиту (SABR streaming / PO Token), которая блокирует скачивание самого видеофайла (`403 Forbidden` / `downloaded file is empty`), даже если страница с видео открывается нормально. Чтобы это обойти, в проекте настроен локальный генератор токена [bgutil-ytdlp-pot-provider](https://github.com/Brainicism/bgutil-ytdlp-pot-provider):

- `.nodeenv/` — своя копия Node.js, не трогает систему
- `.bgutil-provider/` — собранный провайдер (`server/build/generate_once.js`)

`app.py` сам обнаруживает провайдер и Node.js и подключает их к yt-dlp — никаких ручных настроек не требуется. Если понадобится пересобрать провайдер заново:

```bash
source .nodeenv/bin/activate
cd .bgutil-provider/server
npm install
npx tsc
```

(В `package.json` нет скрипта `build`, поэтому компилируем TypeScript напрямую через `npx tsc`.)

**Важно:** версия провайдера должна соответствовать версии yt-dlp — обе используют внутренний, нестабильный API логирования yt-dlp, который иногда меняется. Если после обновления yt-dlp снова появится ошибка вида `debug() got an unexpected keyword argument 'once'` — переустановите провайдер (`pip install -U bgutil-ytdlp-pot-provider`) и пересоберите его тем же способом.

## Если YouTube просит "Sign in to confirm you're not a bot"

Это отдельный, более ранний барьер (на этапе получения информации о видео) — PO Token его не решает, нужны валидные cookies вашего аккаунта:

1. Установите расширение [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
2. Зайдите на youtube.com залогиненным, нажмите на иконку расширения → Export
3. Переместите файл в папку проекта под именем `cookies.txt` (файл в `.gitignore`, в репозиторий не попадёт):
   ```bash
   mv ~/Downloads/youtube.com_cookies.txt ~/Desktop/Claude/youtube-downloader/cookies.txt
   ```

### cookies.txt быстро "протухает"

Google периодически ротирует часть сессионных токенов из соображений безопасности — уже через несколько часов экспортированный `cookies.txt` может перестать работать, и ошибка "Sign in to confirm you're not a bot" вернётся. В этом случае экспортируйте файл заново, непосредственно перед скачиванием.

Альтернатива — не экспортировать файл вручную каждый раз, а разрешить yt-dlp читать куки прямо из браузера (`--cookies-from-browser chrome` в коде вместо `cookiefile`). Для этого нужно один раз вручную подтвердить системный диалог macOS (пароль Keychain для Chrome, либо Full Disk Access для терминала — для Safari), это нельзя настроить автоматически.
